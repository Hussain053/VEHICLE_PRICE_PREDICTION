"""Request and response models for the car price prediction API."""

from pydantic import BaseModel, ConfigDict, Field


class PredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=120)
    year_of_purchase: int = Field(ge=1900, le=2100, description="Year the vehicle was purchased")
    fuel_type: str = Field(min_length=1, max_length=40)
    transmission: str = Field(min_length=1, max_length=40)
    owner_type: str = Field(min_length=1, max_length=40)
    city: str = Field(min_length=1, max_length=80)
    seller_type: str = Field(min_length=1, max_length=40)
    km_driven: int = Field(gt=0, description="Total distance driven in kilometres")
    mileage: float = Field(gt=0, description="Fuel mileage in km/l")
    seating_capacity: int = Field(ge=1, le=30)
    horsepower: float = Field(gt=0, description="Engine power in bhp")
    engine_cc: float = Field(gt=0, description="Engine displacement in cc")


class PredictionResponse(BaseModel):
    predicted_price_inr: float
    formatted_price_inr: str
    currency: str = "INR"
    inputs: PredictionRequest
    reference_year: int
    disclaimer: str = (
        "Estimated advertised listing price; not a guaranteed transaction price."
    )
