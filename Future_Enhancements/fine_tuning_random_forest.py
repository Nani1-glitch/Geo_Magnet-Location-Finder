import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import torch
import torchvision.transforms as transforms
from torch.utils.data import DataLoader
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import joblib
import numpy as np
from PIL import Image
from custom_dataset import CustomDataset
from custom_model import MoCo, load_model

# Define the transformation function
def convert_to_rgb(img):
    return img.convert("RGB") if img.mode != "RGB" else img

def main():
    # File paths
    geo_model_path = "/Users/nithinrajulapati/Downloads/PROJECT 1/output/geography_aware_model.pth"
    moco_model_path = "/Users/nithinrajulapati/Downloads/PROJECT 1/output/moco_model.pth"
    valid_csv_path = '/Users/nithinrajulapati/Downloads/PROJECT 1/output/valid_images.csv'
    image_root_dir = '/Users/nithinrajulapati/Downloads/PROJECT 1/output/images'
    output_model_path = '/Users/nithinrajulapati/Downloads/PROJECT 1/Future_Enhancements/optimized_rf_model_with_features.pkl'

    # Device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Load models
    geo_model = load_model(geo_model_path, model_type='custom')
    moco_model = load_model(moco_model_path, model_type='custom')

    # Load dataset
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.Lambda(convert_to_rgb),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    valid_dataset = CustomDataset(csv_file=valid_csv_path, root_dir=image_root_dir, transform=transform)
    valid_dataloader = DataLoader(valid_dataset, batch_size=32, shuffle=False, num_workers=4)

    # Extract features using the MoCo model
    def extract_features(model, dataloader):
        model.eval()
        features = []
        labels = []
        with torch.no_grad():
            for inputs, label in dataloader:
                inputs = inputs.to(device)
                outputs = model(inputs)
                features.append(outputs.cpu().numpy())
                labels.append(label.cpu().numpy())
        features = np.vstack(features)
        labels = np.vstack(labels)
        return features, labels

    # Extract features from validation set
    geo_features, geo_labels = extract_features(geo_model, valid_dataloader)

    # Debugging prints
    print(f"Geo features shape: {geo_features.shape}")
    print(f"Geo labels shape: {geo_labels.shape}")

    # Ensure consistent lengths of features and labels
    if geo_features.shape[0] != geo_labels.shape[0]:
        min_length = min(geo_features.shape[0], geo_labels.shape[0])
        geo_features = geo_features[:min_length]
        geo_labels = geo_labels[:min_length]

    # Select one dimension from the labels if they are multi-dimensional
    geo_labels = geo_labels[:, 0]

    # Debugging prints
    print(f"Geo features shape after alignment: {geo_features.shape}")
    print(f"Geo labels shape after alignment: {geo_labels.shape}")

    # Split the data
    X_train, X_test, y_train, y_test = train_test_split(geo_features, geo_labels, test_size=0.2, random_state=42)

    # Define the parameter grid
    param_grid = {
        'n_estimators': [100, 200, 300],
        'max_depth': [10, 20, 30],
        'min_samples_split': [2, 5, 10],
        'min_samples_leaf': [1, 2, 4]
    }

    # Initialize the model
    rf = RandomForestRegressor()

    # Initialize GridSearchCV
    grid_search = GridSearchCV(estimator=rf, param_grid=param_grid, cv=3, n_jobs=-1, verbose=2, scoring='r2')

    # Fit the model
    grid_search.fit(X_train, y_train)

    # Get the best parameters and the best model
    best_params = grid_search.best_params_
    best_model = grid_search.best_estimator_

    # Evaluate the best model
    y_pred = best_model.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    # Save the best model
    os.makedirs(os.path.dirname(output_model_path), exist_ok=True)
    joblib.dump(best_model, output_model_path)

    print(f"Best Parameters: {best_params}")
    print(f"Mean Squared Error: {mse}")
    print(f"R-Squared: {r2}")

if __name__ == "__main__":
    main()
