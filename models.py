import os
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import PCA
from sklearn.neighbors import NearestNeighbors
from sklearn.ensemble import RandomForestRegressor
import joblib

DATA_PATH = os.path.join('data', 'chembl.csv')
MODEL_PATH = os.path.join('models', 'pipeline.joblib')

def load_data(path=DATA_PATH):
    if not os.path.exists(path):
        path = os.path.join('data','chembl_sample.csv')
    df = pd.read_csv(path)
    df = df.dropna(subset=['SMILES'])
    required = ['MolWt','LogP','TPSA','HBD','HBA','RotBonds','RingCount']
    for c in required:
        if c not in df.columns:
            df[c] = 0.0
    return df

def build_pipeline(df):
    smiles = df['SMILES'].astype(str).values
    vec = TfidfVectorizer(analyzer='char', ngram_range=(2,4), max_features=2000)
    X = vec.fit_transform(smiles)
    n_comp = min(32, max(2, X.shape[0]-1))
    pca = PCA(n_components=n_comp, random_state=42)
    Xred = pca.fit_transform(X.toarray())
    nn = NearestNeighbors(n_neighbors=10, metric='cosine').fit(Xred)
    props = df[['MolWt','LogP','TPSA','HBD','HBA','RotBonds','RingCount']].fillna(0.0)
    target = (props['LogP'] * 0.3 - props['TPSA'] * 0.02 - props['HBD'] * 0.1 + (props['MolWt'] * 0.0005))
    reg = RandomForestRegressor(n_estimators=50, random_state=42)
    reg.fit(props, target)
    pipeline = {'vectorizer': vec, 'pca': pca, 'nn': nn, 'df': df, 'reg': reg}
    return pipeline

def ensure_models():
    os.makedirs('models', exist_ok=True)
    if os.path.exists(MODEL_PATH):
        try:
            pipeline = joblib.load(MODEL_PATH)
            return pipeline
        except:
            pass
    df = load_data()
    pipeline = build_pipeline(df)
    joblib.dump(pipeline, MODEL_PATH)
    return pipeline

def smiles_to_embedding(smiles, pipeline=None):
    if pipeline is None:
        pipeline = ensure_models()
    vec = pipeline['vectorizer'].transform([smiles])
    emb = pipeline['pca'].transform(vec.toarray())
    return emb[0]

def generate_candidates(s1, s2, topk=3, pipeline=None):
    if pipeline is None:
        pipeline = ensure_models()
    emb1 = smiles_to_embedding(s1, pipeline)
    emb2 = smiles_to_embedding(s2, pipeline)
    alphas = np.linspace(0.1, 0.9, 9)
    df = pipeline['df']
    Xred = pipeline['pca'].transform(pipeline['vectorizer'].transform(df['SMILES'].astype(str)).toarray())
    results = []
    seen = set([s1, s2])
    from sklearn.metrics.pairwise import cosine_distances
    for alpha in alphas:
        vec = (1-alpha)*emb1 + alpha*emb2
        dists = cosine_distances([vec], Xred)[0]
        idxs = np.argsort(dists)[:20]
        for idx in idxs:
            smi = df.iloc[idx]['SMILES']
            if smi in seen: continue
            seen.add(smi)
            props = df.iloc[idx][['MolWt','LogP','TPSA','HBD','HBA','RotBonds','RingCount']].to_dict()
            adme = float(pipeline['reg'].predict([list(df.iloc[idx][['MolWt','LogP','TPSA','HBD','HBA','RotBonds','RingCount']])])[0])
            results.append({'SMILES': smi, 'properties': {k: float(v) for k,v in props.items()}, 'adme_score': adme, 'distance': float(dists[idx])})
            if len(results) >= topk:
                break
        if len(results) >= topk:
            break
    results = sorted(results, key=lambda x: x['distance'])
    return results
