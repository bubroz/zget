import json
import re
import httpx
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from pathlib import Path

from .db.store import VideoStore
from .smokescreen import (
    verify_site,
    verify_sites_batch,
    save_health_log,
    load_health_log,
    HealthResult,
    HealthStatus,
)

SUPPORTED_SITES_URL = "https://raw.githubusercontent.com/yt-dlp/yt-dlp/master/supportedsites.md"
METADATA_MANIFEST_URL = (
    "https://raw.githubusercontent.com/bubroz/zget/main/data/enriched_registry.json"
)

# Top sites to verify on startup (most commonly used)
TOP_SITES = [
    "youtube",
    "tiktok",
    "instagram",
    "twitter",
    "reddit",
    "vimeo",
    "soundcloud",
    "twitch",
    "facebook",
    "dailymotion",
    "bilibili",
    "nicovideo",
    "pornhub",
    "xvideos",
    "bandcamp",
    "spotify",
]

COUNTRY_CODES = {
    "AF": "Afghanistan",
    "AX": "Åland Islands",
    "AL": "Albania",
    "DZ": "Algeria",
    "AS": "American Samoa",
    "AD": "Andorra",
    "AO": "Angola",
    "AI": "Anguilla",
    "AQ": "Antarctica",
    "AG": "Antigua and Barbuda",
    "AR": "Argentina",
    "AM": "Armenia",
    "AW": "Aruba",
    "AU": "Australia",
    "AT": "Austria",
    "AZ": "Azerbaijan",
    "BS": "Bahamas",
    "BH": "Bahrain",
    "BD": "Bangladesh",
    "BB": "Barbados",
    "BY": "Belarus",
    "BE": "Belgium",
    "BZ": "Belize",
    "BJ": "Benin",
    "BM": "Bermuda",
    "BT": "Bhutan",
    "BO": "Bolivia",
    "BA": "Bosnia and Herzegovina",
    "BW": "Botswana",
    "BR": "Brazil",
    "VG": "British Virgin Islands",
    "BN": "Brunei",
    "BG": "Bulgaria",
    "BF": "Burkina Faso",
    "BI": "Burundi",
    "KH": "Cambodia",
    "CM": "Cameroon",
    "CA": "Canada",
    "CV": "Cape Verde",
    "KY": "Cayman Islands",
    "CF": "Central African Republic",
    "TD": "Chad",
    "CL": "Chile",
    "CN": "China",
    "CO": "Colombia",
    "KM": "Comoros",
    "CG": "Congo (Brazzaville)",
    "CD": "Congo (Kinshasa)",
    "CK": "Cook Islands",
    "CR": "Costa Rica",
    "CI": "Côte d'Ivoire",
    "HR": "Croatia",
    "CU": "Cuba",
    "CY": "Cyprus",
    "CZ": "Czech Republic",
    "DK": "Denmark",
    "DJ": "Djibouti",
    "DM": "Dominica",
    "DO": "Dominican Republic",
    "EC": "Ecuador",
    "EG": "Egypt",
    "SV": "El Salvador",
    "GQ": "Equatorial Guinea",
    "ER": "Eritrea",
    "EE": "Estonia",
    "ET": "Ethiopia",
    "FK": "Falkland Islands",
    "FO": "Faroe Islands",
    "FJ": "Fiji",
    "FI": "Finland",
    "FR": "France",
    "GF": "French Guiana",
    "PF": "French Polynesia",
    "GA": "Gabon",
    "GM": "Gambia",
    "GE": "Georgia",
    "DE": "Germany",
    "GH": "Ghana",
    "GI": "Gibraltar",
    "GR": "Greece",
    "GL": "Greenland",
    "GD": "Grenada",
    "GP": "Guadeloupe",
    "GU": "Guam",
    "GT": "Guatemala",
    "GG": "Guernsey",
    "GN": "Guinea",
    "GW": "Guinea-Bissau",
    "GY": "Guyana",
    "HT": "Haiti",
    "HN": "Honduras",
    "HK": "Hong Kong",
    "HU": "Hungary",
    "IS": "Iceland",
    "IN": "India",
    "ID": "Indonesia",
    "IR": "Iran",
    "IQ": "Iraq",
    "IE": "Ireland",
    "IM": "Isle of Man",
    "IL": "Israel",
    "IT": "Italy",
    "JM": "Jamaica",
    "JP": "Japan",
    "JE": "Jersey",
    "JO": "Jordan",
    "KZ": "Kazakhstan",
    "KE": "Kenya",
    "KI": "Kiribati",
    "KP": "Korea (North)",
    "KR": "Korea (South)",
    "KW": "Kuwait",
    "KG": "Kyrgyzstan",
    "LA": "Laos",
    "LV": "Latvia",
    "LB": "Lebanon",
    "LS": "Lesotho",
    "LR": "Liberia",
    "LY": "Libya",
    "LI": "Liechtenstein",
    "LT": "Lithuania",
    "LU": "Luxembourg",
    "MO": "Macao",
    "MK": "Macedonia",
    "MG": "Madagascar",
    "MW": "Malawi",
    "MY": "Malaysia",
    "MV": "Maldives",
    "ML": "Mali",
    "MT": "Malta",
    "MH": "Marshall Islands",
    "MQ": "Martinique",
    "MR": "Mauritania",
    "MU": "Mauritius",
    "YT": "Mayotte",
    "MX": "Mexico",
    "FM": "Micronesia",
    "MD": "Moldova",
    "MC": "Monaco",
    "MN": "Mongolia",
    "ME": "Montenegro",
    "MS": "Montserrat",
    "MA": "Morocco",
    "MZ": "Mozambique",
    "MM": "Myanmar",
    "NA": "Namibia",
    "NR": "Nauru",
    "NP": "Nepal",
    "NL": "Netherlands",
    "NC": "New Caledonia",
    "NZ": "New Zealand",
    "NI": "Nicaragua",
    "NE": "Niger",
    "NG": "Nigeria",
    "NU": "Niue",
    "NF": "Norfolk Island",
    "MP": "Northern Mariana Islands",
    "NO": "Norway",
    "OM": "Oman",
    "PK": "Pakistan",
    "PW": "Palau",
    "PS": "Palestine",
    "PA": "Panama",
    "PG": "Papua New Guinea",
    "PY": "Paraguay",
    "PE": "Peru",
    "PH": "Philippines",
    "PN": "Pitcairn",
    "PL": "Poland",
    "PT": "Portugal",
    "PR": "Puerto Rico",
    "QA": "Qatar",
    "RE": "Réunion",
    "RO": "Romania",
    "RU": "Russian Federation",
    "RW": "Rwanda",
    "BL": "Saint Barthélemy",
    "SH": "Saint Helena",
    "KN": "Saint Kitts and Nevis",
    "LC": "Saint Lucia",
    "MF": "Saint Martin",
    "PM": "Saint Pierre and Miquelon",
    "VC": "Saint Vincent and the Grenadines",
    "WS": "Samoa",
    "SM": "San Marino",
    "ST": "São Tomé and Príncipe",
    "SA": "Saudi Arabia",
    "SN": "Senegal",
    "RS": "Serbia",
    "SC": "Seychelles",
    "SL": "Sierra Leone",
    "SG": "Singapore",
    "SX": "Sint Maarten",
    "SK": "Slovakia",
    "SI": "Slovenia",
    "SB": "Solomon Islands",
    "SO": "Somalia",
    "ZA": "South Africa",
    "GS": "South Georgia and the South Sandwich Islands",
    "SS": "South Sudan",
    "ES": "Spain",
    "LK": "Sri Lanka",
    "SD": "Sudan",
    "SR": "Suriname",
    "SJ": "Svalbard and Jan Mayen",
    "SZ": "Swaziland",
    "SE": "Sweden",
    "CH": "Switzerland",
    "SY": "Syria",
    "TW": "Taiwan",
    "TJ": "Tajikistan",
    "TZ": "Tanzania",
    "TH": "Thailand",
    "TL": "Timor-Leste",
    "TG": "Togo",
    "TK": "Tokelau",
    "TO": "Tonga",
    "TT": "Trinidad and Tobago",
    "TN": "Tunisia",
    "TR": "Turkey",
    "TM": "Turkmenistan",
    "TC": "Turks and Caicos Islands",
    "TV": "Tuvalu",
    "UG": "Uganda",
    "UA": "Ukraine",
    "AE": "United Arab Emirates",
    "GB": "United Kingdom",
    "US": "United States",
    "UY": "Uruguay",
    "UZ": "Uzbekistan",
    "VU": "Vanuatu",
    "VE": "Venezuela",
    "VN": "Vietnam",
    "VI": "Virgin Islands (U.S.)",
    "WF": "Wallis and Futuna",
    "EH": "Western Sahara",
    "YE": "Yemen",
    "ZM": "Zambia",
    "ZW": "Zimbabwe",
    "EU": "Europe",
    "UN": "United Nations",
}


class SiteHealth:
    """Manages the status and health of supported download sites."""

    def __init__(self, store: VideoStore = None):
        self.store = store
        self._matrix: Dict[str, bool] = {}
        self._metadata: Dict[str, Dict] = {}
        self._health_log: Dict[str, Dict] = {}
        self._project_root = Path(__file__).resolve().parent.parent.parent
        self._health_log_path = self._project_root / "data/health_log.json"

    async def get_working_matrix(self) -> Dict[str, bool]:
        """Get the site status matrix, either from cache or fresh."""
        sync_needed = self._check_sync_needed()

        if sync_needed or not self._matrix:
            await self.sync()

        return self._matrix

    def _check_sync_needed(self) -> bool:
        """Check if we need to sync based on last_sync metadata."""
        if not self.store:
            return True

        last_sync_str = self.store.get_metadata("last_registry_sync")
        if not last_sync_str:
            return True

        try:
            last_sync = datetime.fromisoformat(last_sync_str.replace("Z", ""))
            return datetime.utcnow() - last_sync > timedelta(days=7)
        except (ValueError, TypeError):
            return True

    async def sync(self) -> None:
        """Fetch fresh site and metadata status."""
        async with httpx.AsyncClient() as client:
            # 1. Fetch yt-dlp supported sites
            try:
                resp = await client.get(SUPPORTED_SITES_URL, timeout=10.0)
                if resp.status_code == 200:
                    self._matrix = self._parse_markdown(resp.text)
                    if self.store:
                        self.store.set_metadata("cached_site_matrix", json.dumps(self._matrix))
            except Exception:
                if self.store:
                    cached_str = self.store.get_metadata("cached_site_matrix")
                    if cached_str:
                        self._matrix = json.loads(cached_str)

            # 2. Load enriched metadata from local file first
            local_path = self._project_root / "data/enriched_registry.json"

            if local_path.exists():
                try:
                    with open(local_path, "r") as f:
                        self._metadata = json.load(f)
                    if self.store:
                        self.store.set_metadata(
                            "cached_registry_metadata", json.dumps(self._metadata)
                        )
                except Exception:
                    pass

            # Fallback to remote/cache if local not available
            if not self._metadata:
                try:
                    resp = await client.get(METADATA_MANIFEST_URL, timeout=10.0)
                    if resp.status_code == 200:
                        self._metadata = resp.json()
                        if self.store:
                            self.store.set_metadata(
                                "cached_registry_metadata", json.dumps(self._metadata)
                            )
                except Exception:
                    if self.store:
                        cached_str = self.store.get_metadata("cached_registry_metadata")
                        if cached_str:
                            self._metadata = json.loads(cached_str)

        # 3. Load Health Log
        self._health_log = load_health_log(self._health_log_path)

        # Update sync timestamp
        if self.store:
            self.store.set_metadata("last_registry_sync", datetime.utcnow().isoformat() + "Z")

    def _parse_markdown(self, content: str) -> Dict[str, bool]:
        """Parses the yt-dlp Markdown file."""
        results = {}
        lines = content.splitlines()
        for line in lines:
            if not line.strip().startswith("- **"):
                continue

            match = re.search(r"-\s+\*\*([^*]+)\*\*", line)
            if not match:
                continue

            site_name = match.group(1).lower()
            is_broken = "(Currently broken)" in line
            results[site_name] = not is_broken
        return results

    def get_site_info(self, site_name: str) -> Dict:
        """Get enriched info (country, lang, etc) for a site."""
        base_info = {
            "name": site_name,
            "working": self._matrix.get(site_name.lower(), True),
            "country": "Unknown",
            "language": "Universal",
            "description": "No description available.",
        }

        enriched = self._metadata.get(site_name.lower(), {})
        base_info.update(enriched)

        # Merge health verification info
        health_status = self._health_log.get(site_name.lower())
        if health_status:
            base_info["health"] = health_status

        return base_info

    def get_health_status(self, site_name: str) -> Optional[Dict]:
        """Get the latest health verification result for a site."""
        return self._health_log.get(site_name.lower())

    async def verify_single(
        self,
        site_id: str,
        force: bool = False,
        proxy: Optional[str] = None,
        tested_from: str = "local",
    ) -> HealthResult:
        """
        Verify a single site's health on-demand.
        """
        # Check if we have a recent result (within 1 hour)
        existing = self._health_log.get(site_id.lower())
        if existing and not force:
            try:
                verified_at_str = existing.get("verified_at", "")
                verified_at = datetime.fromisoformat(verified_at_str.replace("Z", ""))
                if datetime.utcnow() - verified_at < timedelta(hours=1):
                    return HealthResult(
                        site=site_id,
                        status=HealthStatus(existing["status"]),
                        latency_ms=existing.get("latency_ms", 0),
                        error=existing.get("error"),
                        verified_at=existing["verified_at"],
                        test_url=existing.get("test_url"),
                        tested_from=existing.get("tested_from", "local"),
                    )
            except (ValueError, KeyError):
                pass

        # Get test URL from metadata
        site_meta = self._metadata.get(site_id.lower(), {})
        test_url = site_meta.get("test_url", "")

        result = await verify_site(site_id, test_url, proxy=proxy, tested_from=tested_from)

        # Update health log
        self._health_log[site_id.lower()] = result.to_dict()
        save_health_log([result], self._health_log_path)

        return result

    async def run_smokescreen(
        self,
        sites: Optional[List[str]] = None,
        concurrency: int = 5,
        proxy: Optional[str] = None,
        tested_from: str = "local",
        on_result: Optional[Callable[[HealthResult], None]] = None,
    ) -> List[HealthResult]:
        """
        Run smokescreen verification on multiple sites.
        """
        if sites is None:
            # If nothing specified, try to find sites needing verification
            # For now, just TOP_SITES or all if specifically requested
            sites = TOP_SITES

        # Build site info list with test URLs
        site_infos = []
        for site_id in sites:
            site_meta = self._metadata.get(site_id.lower(), {})
            test_url = site_meta.get("test_url", "")
            site_infos.append({"site": site_id, "test_url": test_url})

        results = await verify_sites_batch(
            site_infos,
            concurrency=concurrency,
            proxy=proxy,
            tested_from=tested_from,
            on_result=on_result,
        )

        # Update health log with all results
        for result in results:
            self._health_log[result.site.lower()] = result.to_dict()
        save_health_log(results, self._health_log_path)

        return results

    def get_all_health_statuses(self) -> Dict[str, Dict]:
        """Get all health statuses from the log."""
        return self._health_log.copy()

    async def get_archive_snapshot(self, domain: str) -> Optional[Dict]:
        """Fetch latest snapshot info from Archive.org Availability API."""
        if not domain or domain == "Unknown":
            return None

        # Clean domain
        clean_domain = domain.split(":")[0].lower()
        if "." not in clean_domain:
            # Try to get domain from metadata if it's just a site name
            meta = self._metadata.get(clean_domain, {})
            clean_domain = meta.get("domain", clean_domain)
            if "." not in clean_domain:
                clean_domain += ".com"

        api_url = f"https://archive.org/wayback/available?url={clean_domain}"

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(api_url, timeout=5.0)
                if resp.status_code == 200:
                    data = resp.json()
                    snapshots = data.get("archived_snapshots", {})
                    closest = snapshots.get("closest")
                    if closest and closest.get("available"):
                        # Parse timestamp 20060101000000 -> 2006-01-01
                        ts = closest.get("timestamp", "")
                        if len(ts) >= 8:
                            formatted_date = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}"
                        else:
                            formatted_date = ts

                        return {
                            "url": closest.get("url"),
                            "timestamp": ts,
                            "date": formatted_date,
                            "available": True,
                        }
        except Exception:
            pass
        return None


async def get_site_intelligence(store: VideoStore) -> Dict[str, bool]:
    """Helper to get site status matrix."""
    health = SiteHealth(store)
    return await health.get_working_matrix()
