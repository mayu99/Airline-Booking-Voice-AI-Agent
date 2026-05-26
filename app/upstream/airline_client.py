import logging
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.config import settings

logger = logging.getLogger("airline_client")

class AirlineClient:
    def __init__(self):
        self.url = settings.UPSTREAM_API_URL
        self.timeout = httpx.Timeout(5.0)

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=1.0),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.NetworkError)),
        reraise=True
    )
    async def search_flights(self, src: str, dst: str, date: str) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            logger.info(f"Calling upstream GET {self.url} with src={src}, dst={dst}, date={date}")
            try:
                response = await client.get(self.url, params={"src": src, "dst": dst, "date": date})
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return {"src": src, "dst": dst, "date": date, "flights": []}
                raise e
            
            if response.status_code == 404:
                return {"src": src, "dst": dst, "date": date, "flights": []}
            
            response.raise_for_status()
            return response.json()

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=1.0),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.NetworkError)),
        reraise=True
    )
    async def book_flight(self, flight_id: str, first_name: str, last_name: str, date: str) -> dict:
        body = {
            "flightId": flight_id,
            "passenger": {
                "firstName": first_name,
                "lastName": last_name
            },
            "date": date
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            logger.info(f"Calling upstream POST {self.url} with flightId={flight_id}")
            response = await client.post(self.url, json=body)
            response.raise_for_status()
            return response.json()

airline_client = AirlineClient()
