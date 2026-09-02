import pandas as pd
from pricing import estimate_price

def load_synthetic(path="training_data.csv"):
    df=pd.read_csv(path)
    df["source"]="synthetic"
    return df[["distance_km", "hour", "is_weekend", "vehicle_type","surge","source"]]

def load_real(path="real_prices.csv"):
    df=pd.read_csv(path)
    surges=[]
    for _, row in df.iterrows():
        result = estimate_price(row["distance_km"], row["hour"], row["is_weekend"]=="True", row["is_rainy"]=="True", row["vehicle_type"])
        surges.append(row["price"]/result["base"])
    df["surge"]=surges
    df["source"]="real"
    return df[["distance_km", "hour", "is_weekend", "vehicle_type","surge", "source"]]

def load_features(real_weight=5):
    synthetic=load_synthetic()
    real=load_real()
#repeating real rows because they need to have more influence during training and are far fewer
    real_weighted=pd.concat([real]*real_weight, ignore_index=True)

    combined=pd.concat([synthetic, real_weighted], ignore_index=True)
    combined["is_weekend"]=combined["is_weekend"].astype(bool).astype(int)

    features=combined[["distance_km", "hour", "is_weekend"]].copy()
    vehicle_dummies = pd.get_dummies(combined["vehicle_type"], prefix="vt")
    features = pd.concat([features, vehicle_dummies], axis=1)

    target = combined["surge"]
    return features, target, list(vehicle_dummies.columns)  
if __name__ == "__main__":
    X, y, vehicle_columns = load_features()
    print(X.head())
    print("Vehicle columns:", vehicle_columns)
    print("Total rows:", len(X))