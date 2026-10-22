export interface ModelOption {
  value: string;
  label: string;
}

export interface CompanyOption {
  value: string;
  label: string;
  models: ModelOption[];
}

export interface NumericLimit {
  min: number;
  max: number;
}

export interface ApiOptions {
  companies: CompanyOption[];
  fuel_options: string[];
  transmission_options: string[];
  owner_options: string[];
  city_options: string[];
  seller_options: string[];
  limits: {
    vehicle_age: NumericLimit;
    km_driven: NumericLimit;
    mileage: NumericLimit;
    horsepower: NumericLimit;
    engine_cc: NumericLimit;
  };
  seating_options: number[];
  reference_year: number;
}

export interface PredictionRequest {
  company: string;
  model: string;
  year_of_purchase: number;
  fuel_type: string;
  transmission: string;
  owner_type: string;
  city: string;
  seller_type: string;
  km_driven: number;
  mileage: number;
  seating_capacity: number;
  horsepower: number;
  engine_cc: number;
}

export interface PredictionResponse {
  predicted_price_inr: number;
  formatted_price_inr: string;
  currency: string;
  inputs: PredictionRequest;
  reference_year: number;
  disclaimer: string;
}
