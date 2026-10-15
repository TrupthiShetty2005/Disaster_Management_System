def to_geojson_stub(payload: dict) -> dict:
    return {"type": "FeatureCollection", "features": [], "meta": payload}
