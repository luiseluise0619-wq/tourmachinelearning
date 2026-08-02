import json
import random
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
import schemas

class FestCastModel:
    def __init__(self):
        self.model = None
        self.is_trained = False
        self.feature_names = [
            'duration_days', 'area_size', 'is_free', 'expected_budget', 'promo_budget',
            'staff_count', 'volunteer_count', 'population', 'tourist_count',
            'foreign_visitors', 'public_transport_access', 'parking_capacity',
            'lodging_count', 'avg_temp', 'rain_prob', 'program_count',
            'has_experience', 'has_food', 'has_celebrity', 'search_volume', 'sns_mentions'
        ]

    def _generate_synthetic_data(self, n_samples=500):
        # Generate some synthetic data to train an initial model
        data = []
        for _ in range(n_samples):
            row = {
                'duration_days': random.randint(1, 14),
                'area_size': random.uniform(1000, 50000),
                'is_free': random.choice([0, 1]),
                'expected_budget': random.uniform(10, 1000) * 10000,
                'promo_budget': random.uniform(1, 100) * 10000,
                'staff_count': random.randint(10, 500),
                'volunteer_count': random.randint(0, 300),
                'population': random.randint(50000, 1000000),
                'tourist_count': random.randint(1000, 100000),
                'foreign_visitors': random.randint(0, 5000),
                'public_transport_access': random.uniform(1.0, 10.0),
                'parking_capacity': random.randint(50, 5000),
                'lodging_count': random.randint(10, 500),
                'avg_temp': random.uniform(5.0, 35.0),
                'rain_prob': random.uniform(0.0, 1.0),
                'program_count': random.randint(1, 30),
                'has_experience': random.choice([0, 1]),
                'has_food': random.choice([0, 1]),
                'has_celebrity': random.choice([0, 1]),
                'search_volume': random.randint(100, 50000),
                'sns_mentions': random.randint(10, 10000),
            }
            # Simple formula for "visitors" target
            base_visitors = (row['population'] * 0.05) + (row['expected_budget'] * 0.1)
            weather_penalty = (row['rain_prob'] * 0.5) if not row['is_free'] else (row['rain_prob'] * 0.2)
            visitors = base_visitors * (1 - weather_penalty) * (1.5 if row['has_celebrity'] else 1.0)

            # Add some noise
            visitors *= np.random.normal(1.0, 0.1)
            row['total_visitors'] = max(100, int(visitors))
            data.append(row)

        return pd.DataFrame(data)

    def train_if_needed(self):
        if not self.is_trained:
            df = self._generate_synthetic_data()
            X = df[self.feature_names]
            y = df['total_visitors']
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

            # Compare Models
            models = {
                'XGBoost': xgb.XGBRegressor(objective='reg:squarederror', n_estimators=100, learning_rate=0.1, random_state=42),
                'RandomForest': RandomForestRegressor(n_estimators=100, random_state=42),
                'GradientBoosting': GradientBoostingRegressor(n_estimators=100, random_state=42)
            }

            best_model = None
            best_mse = float('inf')

            for name, m in models.items():
                m.fit(X_train, y_train)
                preds = m.predict(X_test)
                mse = mean_squared_error(y_test, preds)
                # print(f"Model {name} MSE: {mse}")
                if mse < best_mse:
                    best_mse = mse
                    best_model = m

            self.model = best_model
            self.is_trained = True

    def predict(self, project: schemas.ProjectCreate):
        self.train_if_needed()

        # Build feature vector
        data = {
            'duration_days': project.duration_days,
            'area_size': project.area_size,
            'is_free': 1 if project.is_free else 0,
            'expected_budget': project.expected_budget,
            'promo_budget': project.promo_budget,
            'staff_count': project.staff_count,
            'volunteer_count': project.volunteer_count,
            'population': project.population or 100000,
            'tourist_count': project.tourist_count or 10000,
            'foreign_visitors': project.foreign_visitors or 500,
            'public_transport_access': project.public_transport_access or 5.0,
            'parking_capacity': project.parking_capacity or 500,
            'lodging_count': project.lodging_count or 100,
            'avg_temp': project.avg_temp or 20.0,
            'rain_prob': project.rain_prob or 0.1,
            'program_count': project.program_count or 10,
            'has_experience': 1 if project.has_experience else 0,
            'has_food': 1 if project.has_food else 0,
            'has_celebrity': 1 if project.has_celebrity else 0,
            'search_volume': project.search_volume or 1000,
            'sns_mentions': project.sns_mentions or 500,
        }

        df = pd.DataFrame([data])
        pred = self.model.predict(df)[0]

        # Calculate a pseudo success probability (0-1) based on visitors / budget ratio (just an example metric)
        expected_roi = pred / (project.expected_budget + 1)
        # Normalize to a probability roughly between 0.3 and 0.95
        prob = min(max(0.3, expected_roi * 10), 0.99)

        return int(max(0, pred)), float(prob)

    def get_feature_importance(self):
        self.train_if_needed()
        importance = self.model.feature_importances_
        # Sort and return top 10
        sorted_idx = np.argsort(importance)[::-1][:10]
        result = []
        for idx in sorted_idx:
            result.append({
                "feature": self.feature_names[idx],
                "importance": float(importance[idx])
            })
        return json.dumps(result)

ai_model = FestCastModel()
