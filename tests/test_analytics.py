import pytest
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from api.analytics import (
    calculate_customer_ltv,
    generate_product_recommendations,
    perform_customer_segmentation,
    analyze_market_basket,
    forecast_sales
)

@pytest.fixture
def sample_transaction_data():
    """Create sample transaction data for testing."""
    return pd.DataFrame({
        'customer_id': [1, 1, 2, 2, 3],
        'order_date': pd.date_range(start='2024-01-01', periods=5),
        'order_value': [100, 150, 200, 250, 300],
        'product_id': [1, 2, 1, 3, 2]
    })

@pytest.fixture
def sample_customer_data():
    """Create sample customer data for testing."""
    return pd.DataFrame({
        'customer_id': [1, 2, 3],
        'registration_date': pd.date_range(start='2023-01-01', periods=3),
        'total_orders': [2, 2, 1],
        'total_spend': [250, 450, 300]
    })

@pytest.fixture
def sample_product_data():
    """Create sample product data for testing."""
    return pd.DataFrame({
        'product_id': [1, 2, 3],
        'category': ['A', 'B', 'A'],
        'price': [50, 75, 100],
        'stock': [100, 150, 200]
    })

def test_customer_ltv(sample_transaction_data, sample_customer_data):
    """Test customer lifetime value calculation."""
    ltv_data = calculate_customer_ltv(sample_transaction_data, sample_customer_data)
    
    assert isinstance(ltv_data, pd.DataFrame)
    assert 'customer_id' in ltv_data.columns
    assert 'ltv' in ltv_data.columns
    assert len(ltv_data) == len(sample_customer_data)
    assert all(ltv_data['ltv'] >= 0)  # LTV should not be negative

def test_product_recommendations(sample_transaction_data, sample_product_data):
    """Test product recommendation generation."""
    customer_id = 1
    recommendations = generate_product_recommendations(
        sample_transaction_data,
        sample_product_data,
        customer_id,
        n_recommendations=2
    )
    
    assert isinstance(recommendations, list)
    assert len(recommendations) <= 2  # Should not exceed requested number
    assert all(isinstance(rec, dict) for rec in recommendations)
    if recommendations:
        assert 'product_id' in recommendations[0]
        assert 'score' in recommendations[0]

def test_customer_segmentation(sample_customer_data):
    """Test customer segmentation."""
    segments = perform_customer_segmentation(sample_customer_data)
    
    assert isinstance(segments, pd.DataFrame)
    assert 'customer_id' in segments.columns
    assert 'segment' in segments.columns
    assert len(segments) == len(sample_customer_data)
    assert segments['segment'].nunique() > 0  # Should have at least one segment

def test_market_basket_analysis(sample_transaction_data):
    """Test market basket analysis."""
    basket_insights = analyze_market_basket(sample_transaction_data)
    
    assert isinstance(basket_insights, list)
    if basket_insights:
        assert 'antecedents' in basket_insights[0]
        assert 'consequents' in basket_insights[0]
        assert 'confidence' in basket_insights[0]
        assert 0 <= basket_insights[0]['confidence'] <= 1

def test_sales_forecasting(sample_transaction_data):
    """Test sales forecasting."""
    forecast_periods = 7
    forecast = forecast_sales(sample_transaction_data, periods=forecast_periods)
    
    assert isinstance(forecast, pd.DataFrame)
    assert len(forecast) == forecast_periods
    assert 'forecast' in forecast.columns
    assert 'lower_bound' in forecast.columns
    assert 'upper_bound' in forecast.columns
    assert all(forecast['lower_bound'] <= forecast['forecast'])
    assert all(forecast['forecast'] <= forecast['upper_bound'])

def test_empty_data_handling():
    """Test handling of empty data."""
    empty_df = pd.DataFrame()
    
    # Test each analytics function with empty data
    with pytest.raises(ValueError):
        calculate_customer_ltv(empty_df, empty_df)
    
    with pytest.raises(ValueError):
        generate_product_recommendations(empty_df, empty_df, customer_id=1)
    
    with pytest.raises(ValueError):
        perform_customer_segmentation(empty_df)
    
    with pytest.raises(ValueError):
        analyze_market_basket(empty_df)
    
    with pytest.raises(ValueError):
        forecast_sales(empty_df)

def test_data_validation():
    """Test input data validation."""
    invalid_data = pd.DataFrame({
        'wrong_column': [1, 2, 3]
    })
    
    # Test each analytics function with invalid data
    with pytest.raises(ValueError):
        calculate_customer_ltv(invalid_data, invalid_data)
    
    with pytest.raises(ValueError):
        generate_product_recommendations(invalid_data, invalid_data, customer_id=1)
    
    with pytest.raises(ValueError):
        perform_customer_segmentation(invalid_data)
    
    with pytest.raises(ValueError):
        analyze_market_basket(invalid_data)
    
    with pytest.raises(ValueError):
        forecast_sales(invalid_data)

def test_edge_cases():
    """Test edge cases in analytics functions."""
    # Single customer data
    single_customer = pd.DataFrame({
        'customer_id': [1],
        'total_orders': [1],
        'total_spend': [100]
    })
    
    segments = perform_customer_segmentation(single_customer)
    assert len(segments) == 1
    
    # Single transaction data
    single_transaction = pd.DataFrame({
        'customer_id': [1],
        'order_date': [datetime.now()],
        'order_value': [100],
        'product_id': [1]
    })
    
    forecast = forecast_sales(single_transaction)
    assert isinstance(forecast, pd.DataFrame)
    
    # Test with very large values
    large_value_data = pd.DataFrame({
        'customer_id': [1],
        'total_orders': [1000000],
        'total_spend': [1e9]
    })
    
    ltv = calculate_customer_ltv(single_transaction, large_value_data)
    assert not np.isinf(ltv['ltv'].iloc[0]) 