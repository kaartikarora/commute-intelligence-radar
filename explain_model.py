import shap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from features import load_features
from model import load_model
def explain():
    model, vehicle_columns=load_model()
    X,y,_=load_features()

    #shap's method for tree based models
    explainer=shap.TreeExplainer(model)
    shap_values=explainer.shap_values(X)

    shap.summary_plot(shap_values, X, show=False)
    plt.tight_layout()
    plt.savefig("shap_summary.png", bbox_inches="tight")
    plt.close()
    print("SHAP_Summary Saved")

    shap.dependence_plot("distance_km", shap_values, X, show=False)
    plt.tight_layout()
    plt.savefig("shap_distance.png", bbox_inches="tight")
    plt.close()
    print("shap_distance.png saved")
if __name__ == "__main__":
    explain()