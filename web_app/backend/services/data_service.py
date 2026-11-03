import os
from pathlib import Path
import pandas as pd
import numpy as np

WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent
DEFAULT_DATA_PATH = WORKSPACE_ROOT / "data" / "ev_stations_2025.csv"

class DataService:
    def __init__(self):
        self.default_data_path = DEFAULT_DATA_PATH
        self.current_df = None
        self.is_custom = False
        self.custom_filename = None
        self.load_data()

    def load_data(self):
        """Load default dataset and preprocess."""
        if os.path.exists(self.default_data_path):
            df = pd.read_csv(self.default_data_path)
            self.current_df = self._preprocess(df)
            self.is_custom = False
            self.custom_filename = None
        else:
            raise FileNotFoundError(f"Default dataset not found at {self.default_data_path}")

    def load_custom_data(self, file_content: bytes, filename: str):
        """Validate and load custom CSV dataset."""
        import io
        try:
            raw_df = pd.read_csv(io.BytesIO(file_content))
        except Exception as e:
            raise ValueError(f"Failed to parse CSV: {str(e)}")

        required_cols = ["lat", "lon", "state", "status", "operator", "num_connectors"]
        missing = [c for c in required_cols if c not in raw_df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(missing)}")

        valid_coords = (
            pd.to_numeric(raw_df['lat'], errors='coerce').notna() &
            pd.to_numeric(raw_df['lon'], errors='coerce').notna()
        )
        if valid_coords.sum() == 0:
            raise ValueError("No valid latitude/longitude coordinates found in dataset.")

        self.current_df = self._preprocess(raw_df)
        self.is_custom = True
        self.custom_filename = filename
        return self.get_summary_stats()

    def reset_to_default(self):
        """Reset back to bundled dataset."""
        self.load_data()
        return self.get_summary_stats()

    def _preprocess(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        if 'id' not in df.columns:
            df['id'] = range(1, len(df) + 1)
        
        df['num_connectors'] = pd.to_numeric(df['num_connectors'], errors='coerce').fillna(1.0)
        df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
        df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
        
        if 'status' in df.columns:
            status_clean = df['status'].astype(str).str.strip().str.lower()
            df['is_operational'] = status_clean == 'operational'
            df['is_offline'] = status_clean.isin(['temporarily unavailable', 'not operational', 'offline'])
            df['is_planned_unknown'] = ~df['is_operational'] & ~df['is_offline']
        else:
            df['is_operational'] = True
            df['is_offline'] = False
            df['is_planned_unknown'] = False
            
        if 'state' in df.columns:
            df['state_clean'] = df['state'].astype(str).str.strip()
            df.loc[df['state'].isna(), 'state_clean'] = np.nan
        else:
            df['state_clean'] = np.nan

        if 'country' in df.columns:
            df['country_clean'] = df['country'].astype(str).str.strip().str.upper()
            df.loc[df['country'].isna(), 'country_clean'] = 'UNKNOWN'
        else:
            df['country_clean'] = 'UNKNOWN'
            
        if 'operator' not in df.columns:
            df['operator'] = 'Unknown Operator'
        else:
            df['operator'] = df['operator'].fillna('Unknown Operator')

        if 'title' not in df.columns:
            df['title'] = 'Charging Station #' + df['id'].astype(str)
        else:
            df['title'] = df['title'].fillna('Charging Station #' + df['id'].astype(str))

        return df

    def get_df(self) -> pd.DataFrame:
        return self.current_df

    def get_summary_stats(self) -> dict:
        df = self.current_df
        total_stations = len(df)
        total_connectors = int(df['num_connectors'].sum())
        avg_connectors = round(float(total_connectors / total_stations), 2) if total_stations > 0 else 0
        operational_count = int(df['is_operational'].sum())
        offline_count = int(df['is_offline'].sum()) if 'is_offline' in df.columns else 0
        planned_unknown_count = int(df['is_planned_unknown'].sum()) if 'is_planned_unknown' in df.columns else 0
        operational_ratio = round(float(operational_count / total_stations), 4) if total_stations > 0 else 0
        
        valid_states = df['state_clean'].dropna()
        num_states = int(valid_states.nunique())
        missing_states = int(df['state_clean'].isna().sum())
        
        # Regional breakdown (top 10)
        if num_states > 0:
            reg_stats = df.dropna(subset=['state_clean']).groupby('state_clean').agg(
                stations=('id', 'count'),
                connectors=('num_connectors', 'sum')
            ).sort_values('stations', ascending=False).head(10)
            
            top_regions = [
                {
                    "state": state,
                    "stations": int(row['stations']),
                    "connectors": int(row['connectors']),
                    "cps": round(float(row['connectors'] / row['stations']), 2)
                }
                for state, row in reg_stats.iterrows()
            ]
        else:
            top_regions = []

        # Operator breakdown (top 10)
        op_stats = df.groupby('operator').agg(
            stations=('id', 'count'),
            connectors=('num_connectors', 'sum')
        ).sort_values('stations', ascending=False).head(10)
        
        top_operators = [
            {
                "operator": str(op),
                "stations": int(row['stations']),
                "connectors": int(row['connectors'])
            }
            for op, row in op_stats.iterrows()
        ]

        # Missing value breakdown
        missing_fields = {
            col: int(df[col].isna().sum())
            for col in df.columns if col not in ['state_clean', 'is_operational', 'is_offline', 'is_planned_unknown']
        }

        return {
            "is_custom": self.is_custom,
            "filename": self.custom_filename or "ev_stations_2025.csv",
            "total_stations": total_stations,
            "total_connectors": total_connectors,
            "avg_connectors": avg_connectors,
            "operational_count": operational_count,
            "offline_count": offline_count,
            "planned_unknown_count": planned_unknown_count,
            "operational_ratio": operational_ratio,
            "num_states": num_states,
            "missing_states": missing_states,
            "top_regions": top_regions,
            "top_operators": top_operators,
            "missing_fields": missing_fields
        }

    def get_stations_sample(self, limit: int = 1000, country: str = None, state: str = None, operator: str = None, status: str = None) -> dict:
        """Return structured station objects for mapping and explorer table."""
        df = self.current_df.dropna(subset=['lat', 'lon']).copy()

        if country and country != 'All':
            df = df[df['country_clean'] == country.upper()]
        if state and state != 'All':
            df = df[df['state_clean'] == state]
        if operator and operator != 'All':
            df = df[df['operator'] == operator]
        if status == 'Operational':
            df = df[df['is_operational'] == True]
        elif status == 'Offline':
            df = df[df['is_offline'] == True]
        elif status in ['Planned / Unknown', 'Planned-Unknown', 'Planned']:
            df = df[df['is_planned_unknown'] == True]
        elif status == 'Non-Operational':
            df = df[df['is_operational'] == False]

        total_filtered = len(df)
        
        # Sample if too large for requested limit
        if len(df) > limit:
            sample_df = df.sample(n=limit, random_state=42)
        else:
            sample_df = df

        stations = []
        for _, row in sample_df.iterrows():
            stations.append({
                "id": int(row['id']),
                "title": str(row['title']),
                "lat": float(row['lat']),
                "lon": float(row['lon']),
                "country": str(row.get('country_clean', 'UNKNOWN')),
                "state": str(row['state_clean']) if pd.notna(row['state_clean']) else "Unknown",
                "operator": str(row['operator']),
                "num_connectors": int(row['num_connectors']),
                "is_operational": bool(row['is_operational']),
                "is_offline": bool(row.get('is_offline', False)),
                "is_planned_unknown": bool(row.get('is_planned_unknown', False)),
                "status": str(row.get('status', 'Operational'))
            })

        return {
            "total_filtered": total_filtered,
            "returned_count": len(stations),
            "stations": stations
        }

    def get_filter_options(self) -> dict:
        df = self.current_df
        states = sorted([str(s) for s in df['state_clean'].dropna().unique() if str(s) != 'nan'])
        operators = sorted([str(op) for op in df['operator'].dropna().unique() if str(op) != 'nan'])
        
        COUNTRY_NAMES = {
            "CA": "Canada", "US": "United States", "ES": "Spain", "RU": "Russia",
            "MY": "Malaysia", "TR": "Turkey", "DK": "Denmark", "BR": "Brazil",
            "IT": "Italy", "FR": "France", "DE": "Germany", "GB": "United Kingdom",
            "NL": "Netherlands", "SE": "Sweden", "NO": "Norway", "AU": "Australia"
        }
        countries = []
        if 'country_clean' in df.columns:
            cnt_series = df['country_clean'].value_counts()
            for code, cnt in cnt_series.items():
                if code in ['UNKNOWN', 'NAN']:
                    continue
                name = COUNTRY_NAMES.get(code, code)
                country_sub = df[df['country_clean'] == code]
                num_regions = int(country_sub['state_clean'].dropna().nunique())
                countries.append({
                    "code": code,
                    "name": f"{name} ({code})",
                    "count": int(cnt),
                    "regions_count": num_regions
                })

        return {
            "countries": countries,
            "states": states,
            "operators": operators,
            "statuses": ["All", "Operational", "Offline", "Planned / Unknown", "Non-Operational"]
        }

data_service = DataService()
