import os
import logging
import pandas as pd
from rapidfuzz import process, fuzz
from typing import Dict, Any

logger = logging.getLogger("airports_service")

# Global reference to eager loaded DataFrame
_airports_df = None

def load_airports_data():
    """
    Eagerly loads data/airports.dat into a pandas DataFrame.
    Drops rows where IATA code is missing or not a 3-letter uppercase alphabetic string.
    Combines city and airport_name columns for optimal matching.
    """
    global _airports_df
    if _airports_df is not None:
        return

    filepath = os.path.join("data", "airports.dat")
    logger.info(f"Eagerly loading airports data from {filepath}...")
    
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Airports data file not found at {filepath}")
    
    # OpenFlights airports schema:
    # 0: ID, 1: Name, 2: City, 3: Country, 4: IATA, 5: ICAO, 6: Lat, 7: Lon, 8: Alt, 9: TZ, 10: DST, 11: TZName, 12: Type, 13: Source
    columns = [
        "airport_id", "airport_name", "city", "country", "iata", "icao",
        "lat", "lon", "alt", "tz", "dst", "tz_name", "type", "source"
    ]
    
    # Load into dataframe
    df = pd.read_csv(filepath, names=columns, header=None, na_values=["\\N", "NaN"])
    
    # Clean IATA codes
    df = df[df["iata"].notna()]
    df["iata"] = df["iata"].astype(str).str.strip().str.upper()
    df = df[df["iata"].str.len() == 3]
    
    df["city"] = df["city"].fillna("").astype(str).str.strip()
    df["airport_name"] = df["airport_name"].fillna("").astype(str).str.strip()
    df["country"] = df["country"].fillna("").astype(str).str.strip()
    
    # Create prominence helper flags for sorting
    df["is_us"] = df["country"] == "United States"
    df["is_intl"] = df["airport_name"].str.contains("International", case=False, na=False)
    
    # Eagerly sort so that United States and International airports are prioritized
    df = df.sort_values(by=["is_us", "is_intl"], ascending=[False, False])
    
    # Combined column for search matching
    df["search_text"] = df["city"] + " " + df["airport_name"]
    
    _airports_df = df.reset_index(drop=True)
    logger.info(f"Successfully eager loaded and sorted {len(_airports_df)} airports.")

def resolve_airport(query: str) -> Dict[str, Any]:
    """
    Resolves an airport query using rapidfuzz string matching.
    confidence >= 0.85 -> resolved
    0.60 <= confidence < 0.85 -> ambiguous (top 3)
    confidence < 0.60 -> unknown
    """
    global _airports_df
    if _airports_df is None:
        load_airports_data()
        
    df = _airports_df
    query_stripped = query.strip()
    
    # Direct IATA match check
    if len(query_stripped) == 3 and query_stripped.isalpha():
        iata_match = df[df["iata"] == query_stripped.upper()]
        if not iata_match.empty:
            row = iata_match.iloc[0]
            return {
                "status": "resolved",
                "iata": row["iata"],
                "airport_name": row["airport_name"],
                "city": row["city"],
                "country": row["country"],
                "confidence": 1.0
            }
            
    # Perform rapidfuzz process.extract
    choices = df["search_text"].tolist()
    matches = process.extract(query, choices, scorer=fuzz.WRatio, limit=15)
    
    if not matches:
        return {"status": "unknown", "query": query}
        
    # Map matches and apply a custom boost if query is in the airport name
    matched_rows = []
    for text, score, idx in matches:
        row = df.iloc[idx]
        boosted_score = score
        if query_stripped.lower() in row["airport_name"].lower():
            boosted_score += 10.0
        matched_rows.append((row, boosted_score))
        
    # Sort again by the boosted score
    matched_rows = sorted(matched_rows, key=lambda x: x[1], reverse=True)
    
    best_score = matched_rows[0][1]
    # Bound best_score to 100 for confidence calculation
    best_confidence = round(min(best_score, 100.0) / 100.0, 2)
    
    # If even boosted best score is less than 60, it is unknown
    if best_confidence < 0.60:
        return {"status": "unknown", "query": query}
        
    # Tie-breaking logic: Find all matches with score within 2 points of best_score
    # that are at least 85 and are in the United States
    high_threshold = max(85.0, best_score - 2.0)
    us_high_matches = [
        (row, score) for row, score in matched_rows
        if score >= high_threshold and row["country"] == "United States"
    ]
    
    # If multiple high-scoring matches in the US exist (e.g. New York -> JFK & LGA), it is ambiguous
    if len(us_high_matches) >= 2:
        candidates = []
        seen_iata = set()
        
        # Include high-scoring US ones first
        for row, score in us_high_matches:
            iata = row["iata"]
            if iata not in seen_iata:
                seen_iata.add(iata)
                candidates.append({
                    "iata": iata,
                    "city": row["city"],
                    "country": row["country"]
                })
                
        # Fill candidates to top 3 from other matched rows if needed
        if len(candidates) < 3:
            for row, score in matched_rows:
                iata = row["iata"]
                if iata not in seen_iata:
                    seen_iata.add(iata)
                    candidates.append({
                        "iata": iata,
                        "city": row["city"],
                        "country": row["country"]
                    })
                    if len(candidates) == 3:
                        break
        return {
            "status": "ambiguous",
            "candidates": candidates[:3]
        }
        
    # If exactly one high-scoring match in the US, resolve to it!
    if len(us_high_matches) == 1:
        row, score = us_high_matches[0]
        return {
            "status": "resolved",
            "iata": row["iata"],
            "airport_name": row["airport_name"],
            "city": row["city"],
            "country": row["country"],
            "confidence": round(min(score, 100.0) / 100.0, 2)
        }
        
    # If no US high matches but the top match has confidence >= 0.85
    if best_confidence >= 0.85:
        row, score = matched_rows[0]
        return {
            "status": "resolved",
            "iata": row["iata"],
            "airport_name": row["airport_name"],
            "city": row["city"],
            "country": row["country"],
            "confidence": best_confidence
        }
        
    # Fallback to standard 0.60 - 0.85 ambiguous list
    candidates = []
    seen_iata = set()
    for row, score in matched_rows:
        if score >= 60:
            iata = row["iata"]
            if iata not in seen_iata:
                seen_iata.add(iata)
                candidates.append({
                    "iata": iata,
                    "city": row["city"],
                    "country": row["country"]
                })
                if len(candidates) == 3:
                    break
    if candidates:
        return {
            "status": "ambiguous",
            "candidates": candidates
        }
        
    return {"status": "unknown", "query": query}
