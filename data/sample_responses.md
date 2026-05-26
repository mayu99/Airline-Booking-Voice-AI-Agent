# Upstream Airline API — Real Response Samples

## Base URL
https://zz1mpoguje.execute-api.us-east-1.amazonaws.com/default/airline-assessment

## Test 1 — Search Flights (Happy Path)
GET ?src=JFK&dst=LAX&date=2026-07-15
Status: 200 OK

```json
{
  "src": "JFK",
  "dst": "LAX",
  "date": "2026-07-15",
  "flights": [
    {
      "flightId": "3c577ea13f6b8b1f52a361c187c34fb1",
      "airline": "JetBlue Airways",
      "flightNumber": "JA927",
      "departureTime": "2026-07-15T13:01:00.000Z",
      "arrivalTime": "2026-07-15T18:31:00.000Z",
      "durationMinutes": 330,
      "stops": 0,
      "price": 493.85
    },
    {
      "flightId": "02f95249bf347a878f8320b8945d1a9f",
      "airline": "JetBlue Airways",
      "flightNumber": "JA418",
      "departureTime": "2026-07-15T13:19:00.000Z",
      "arrivalTime": "2026-07-15T14:40:00.000Z",
      "durationMinutes": 81,
      "stops": 0,
      "price": 348.28
    },
    {
      "flightId": "39023fbe9e64da5b7407eea7898c9762",
      "airline": "United Airlines",
      "flightNumber": "UA893",
      "departureTime": "2026-07-15T19:55:00.000Z",
      "arrivalTime": "2026-07-15T21:44:00.000Z",
      "durationMinutes": 109,
      "stops": 0,
      "price": 121.95
    },
    {
      "flightId": "b460b00b40f32ec75e71e18030928af8",
      "airline": "American Airlines",
      "flightNumber": "AA792",
      "departureTime": "2026-07-15T20:40:00.000Z",
      "arrivalTime": "2026-07-16T02:03:00.000Z",
      "durationMinutes": 323,
      "stops": 0,
      "price": 135.59
    },
    {
      "flightId": "65cbbf49b8a721526b8dba245f41ca25",
      "airline": "Southwest Airlines",
      "flightNumber": "SA468",
      "departureTime": "2026-07-15T17:42:00.000Z",
      "arrivalTime": "2026-07-15T23:18:00.000Z",
      "durationMinutes": 336,
      "stops": 0,
      "price": 390.40
    }
  ]
}
```

## Test 2 — Search Flights (No Flights — AAL→YVR edge case)
GET ?src=AAL&dst=YVR&date=2026-07-15
Status: 404 Not Found

```json
{
  "src": "AAL",
  "dst": "YVR",
  "date": "2026-07-15",
  "flights": []
}
```

## Test 3 — Book Flight (Success)
POST ?src=JFK&dst=LAX&date=2026-07-15
Body: {"flightId":"e3a0b6f0fa9b8c3c12c72fb32ad9c7d0","passenger":{"firstName":"Jane","lastName":"Doe"},"date":"2026-07-15"}
Status: 200 OK

```json
{
  "success": true,
  "message": "Flight booked successfully.",
  "confirmationNumber": "CONF154648",
  "flightId": "e3a0b6f0fa9b8c3c12c72fb32ad9c7d0",
  "passenger": {
    "firstName": "Jane",
    "lastName": "Doe"
  }
}
```

## Test 4 — Book Flight (Invalid Date)
Status: 400 Bad Request

```json
{
  "error": "Date must be today or within 1 year."
}
```

## Key Schema Notes for Backend
- confirmationNumber format: "CONF" + 6 digits
- departureTime/arrivalTime: ISO 8601 UTC — convert to local time for voice
- durationMinutes: convert to "X hours Y minutes" for voice
- stops: 0 = nonstop, >0 = with stops
- price: USD float, round to 2 decimal places
- AAL→YVR: returns HTTP 404 with empty flights array
- Date validation: API returns 400 if date invalid