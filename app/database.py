import sqlite3
from datetime import datetime

import pandas as pd
from pathlib import Path
from contextlib import contextmanager

from configurations import DEFAULT_WEIGHT_TYPE, NNR_PREMIUM_FEES, UNILOG_PREMIUM_FEES, FUEL_SURCHARGE


class Database:
    def __init__(self, db_path: str = "data/shipping.db"):
        self.db_path = Path(db_path)
        self.initialize_db()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def initialize_db(self):
        """Create database tables if they don't exist"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Create price list table
            cursor.execute("""
                            CREATE TABLE IF NOT EXISTS price_list (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                weight_range TEXT NOT NULL,
                                zone TEXT NOT NULL,
                                rate REAL NOT NULL,
                                service_level TEXT NOT NULL,
                                country TEXT NOT NULL,
                                type TEXT NOT NULL,
                                min_weight REAL NOT NULL,
                                max_weight REAL NOT NULL
                            )
                        """)

            # Create zones table
            cursor.execute("""
                            CREATE TABLE IF NOT EXISTS zones (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                country TEXT NOT NULL,
                                zip_prefix TEXT NOT NULL,
                                zone TEXT NOT NULL
                            )
                        """)

            # Create extra fees table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS extra_fees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fee_type TEXT NOT NULL,
                    amount REAL NOT NULL,
                    condition TEXT,
                    apply_to TEXT
                )
            """)

            # Add calculation history table
            cursor.execute("""
                        CREATE TABLE IF NOT EXISTS calculation_history (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp TEXT NOT NULL,
                            country TEXT NOT NULL,
                            zipcode TEXT NOT NULL,
                            service_level TEXT NOT NULL,
                            num_collo INTEGER NOT NULL,
                            length REAL NOT NULL,
                            width REAL NOT NULL,
                            height REAL NOT NULL,
                            actual_weight REAL NOT NULL,
                            volume_weight REAL NOT NULL,
                            loading_meter_weight REAL NOT NULL,
                            chargeable_weight REAL NOT NULL,
                            weight_type TEXT NOT NULL,
                            zone TEXT NOT NULL,
                            base_rate REAL NOT NULL,
                            extra_fees REAL NOT NULL,
                            total_price REAL NOT NULL
                        )
                    """)

            # Add configurations table
            cursor.execute("""
                        CREATE TABLE IF NOT EXISTS configurations (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT UNIQUE NOT NULL,
                            value TEXT NOT NULL,
                            updated_at TEXT NOT NULL
                        )
                    """)

            # Initialize default configurations if they don't exist
            self.initialize_default_configs()

            conn.commit()

    def load_excel_data(self, excel_path: str):
        """Load data from Excel file into SQLite database"""
        with self.get_connection() as conn:
            # Load price list
            df_prices = pd.read_excel(excel_path, sheet_name="pricelist")

            # Rename columns to normalized format
            df_prices = df_prices.rename(columns={
                'Weight': 'weight_range',
                'Zone': 'zone',
                'Rate': 'rate',
                'Service level': 'service_level',
                'Country': 'country',  # Note the trailing space
                'Type': 'type'
            })

            # Clean string columns
            string_columns = ['weight_range', 'zone', 'service_level', 'country', 'type']
            for col in string_columns:
                df_prices[col] = df_prices[col].astype(str).apply(lambda x: x.strip())

            # Extract min and max weights
            def extract_weights(weight_range):
                if isinstance(weight_range, str) and '-' in weight_range:
                    min_w, max_w = map(float, weight_range.split('-'))
                else:
                    min_w = max_w = float(weight_range)
                return pd.Series({'min_weight': min_w, 'max_weight': max_w})

            # Add min and max weight columns
            weight_ranges = df_prices['weight_range'].apply(extract_weights)
            df_prices = pd.concat([df_prices, weight_ranges], axis=1)

            # Save to database
            df_prices.to_sql('price_list', conn, if_exists='replace', index=False)

            # Load zones
            df_zones = pd.read_excel(excel_path, sheet_name="zones")

            # Convert Value to string format with zero-padding for numbers
            def format_zip_prefix(x):
                if pd.isna(x):
                    return None
                if isinstance(x, (int, float)):
                    return f"{int(x):02}"
                return str(x).strip()

            df_zones['Value'] = df_zones['Value'].apply(format_zip_prefix)

            # Rename columns
            df_zones = df_zones.rename(columns={
                'Country': 'country',
                'Zone': 'zone',
                'Value': 'zip_prefix'
            })

            # Clean string columns
            for col in ['country', 'zone']:
                df_zones[col] = df_zones[col].astype(str).apply(lambda x: x.strip())

            df_zones.to_sql('zones', conn, if_exists='replace', index=False)

    def get_zone_for_zipcode(self, country: str, zipcode: str) -> str:
        """Get zone based on country and zip code"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Format the prefix
            prefix = str(zipcode)[:2]
            if prefix.isdigit():
                zip_prefix = f"{int(prefix):02}"
            else:
                zip_prefix = prefix

            # Get matching zone
            cursor.execute("""
                SELECT zone 
                FROM zones 
                WHERE country = ? AND zip_prefix = ?
            """, (str(country).strip(), zip_prefix))

            result = cursor.fetchone()
            if not result:
                # If no zone found, get available zones for this country
                cursor.execute("""
                    SELECT zip_prefix, zone
                    FROM zones
                    WHERE country = ?
                    ORDER BY zip_prefix
                """, (str(country).strip(),))

                available_zones = cursor.fetchall()
                if available_zones:
                    zones_str = ", ".join(f"{z[0]} -> {z[1]}" for z in available_zones)
                    raise ValueError(
                        f"No zone found for country {country} and zip code prefix '{zip_prefix}'. "
                        f"Available prefixes and zones: {zones_str}"
                    )
                else:
                    raise ValueError(f"No zones defined for country {country}")

            return str(result[0]).strip()

    def get_rate_for_shipment(self, weight: float, zone: str, service_level: str, country: str) -> float:
        """Get shipping rate based on weight, zone, and service level"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Clean inputs
            zone = str(zone).strip()
            service_level = str(service_level).strip()
            country = str(country).strip()

            cursor.execute("""
                SELECT rate
                FROM price_list
                WHERE zone = ?
                AND service_level = ?
                AND min_weight <= ?
                AND max_weight >= ?
                AND country = ?
                ORDER BY min_weight
                LIMIT 1
            """, (zone, service_level, float(weight), float(weight), country))

            result = cursor.fetchone()
            if not result or result[0] is None:
                raise ValueError(
                    f"No rate found for weight {weight}kg in zone {zone} "
                    f"with service level {service_level} and country {country}"
                )

            return float(result[0])

    def get_extra_fees(self, weight: float, country: str) -> list:
        """Get applicable extra fees"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT fee_type, amount, condition
                FROM extra_fees
                WHERE apply_to = ? OR apply_to IS NULL
            """, (country,))

            return cursor.fetchall()

    def add_calculation_history(self, calculation_data: dict):
        """Add a calculation to history"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO calculation_history (
                    timestamp, country, zipcode, service_level, num_collo,
                    length, width, height, actual_weight, volume_weight,
                    loading_meter_weight, chargeable_weight, weight_type,
                    zone, base_rate, extra_fees, total_price
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            """, (
                calculation_data['timestamp'],
                calculation_data['country'],
                calculation_data['zipcode'],
                calculation_data['service_level'],
                calculation_data['num_collo'],
                calculation_data['length'],
                calculation_data['width'],
                calculation_data['height'],
                calculation_data['actual_weight'],
                calculation_data['volume_weight'],
                calculation_data['loading_meter_weight'],
                calculation_data['chargeable_weight'],
                calculation_data['weight_type'],
                calculation_data['zone'],
                calculation_data['base_rate'],
                calculation_data['extra_fees'],
                calculation_data['total_price']
            ))
            conn.commit()

    def get_calculation_history(self) -> list:
        """Get all calculation history"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM calculation_history
                ORDER BY timestamp DESC
            """)
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def initialize_default_configs(self):
        """Initialize default configurations if they don't exist"""
        default_configs = {
            'DEFAULT_WEIGHT_TYPE': DEFAULT_WEIGHT_TYPE,
            'NNR_PREMIUM_FEES': NNR_PREMIUM_FEES,
            'UNILOG_PREMIUM_FEES': UNILOG_PREMIUM_FEES,
            'FUEL_SURCHARGE': FUEL_SURCHARGE
        }

        for name, value in default_configs.items():
            self.set_config(name, value, initialize=True)

    def get_all_configs(self) -> dict:
        """Get all configurations"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, value FROM configurations")
            return {row[0]: row[1] for row in cursor.fetchall()}

    def get_config(self, name: str, default: str = None) -> str:
        """Get configuration value by name"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT value FROM configurations WHERE name = ?",
                (name,)
            )
            result = cursor.fetchone()
            return result[0] if result else default

    def set_config(self, name: str, value: str, initialize: bool = False) -> None:
        """Set configuration value"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            if initialize:
                # Only set if doesn't exist
                cursor.execute("""
                    INSERT OR IGNORE INTO configurations (name, value, updated_at)
                    VALUES (?, ?, ?)
                """, (name, str(value), current_time))
            else:
                # Update or insert
                cursor.execute("""
                    INSERT OR REPLACE INTO configurations (name, value, updated_at)
                    VALUES (?, ?, ?)
                """, (name, str(value), current_time))

            conn.commit()