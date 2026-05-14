# app/fetchers/cve_fetcher.py
#
# Obtiene CVEs criticos y altos de la NVD API (National Vulnerability Database)
# Documentacion oficial: https://nvd.nist.gov/developers/vulnerabilities
#
# La API es publica y gratuita. Con API key: 50 req/30s. Sin key: 5 req/30s.

import httpx
import os
from datetime import datetime, timedelta, timezone

NVD_BASE_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"


async def fetch_critical_cves(days_back: int = 7) -> list[dict]:
    """
    Consulta la NVD API y devuelve CVEs con CVSS >= 7.0 de los ultimos N dias.
    Ordena por severidad descendente (critical primero).
    """

    # Rango de fechas en formato ISO 8601 que espera la NVD API
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days_back)

    params = {
        "pubStartDate": start_date.strftime("%Y-%m-%dT%H:%M:%S.000"),
        "pubEndDate": end_date.strftime("%Y-%m-%dT%H:%M:%S.000"),
        "cvssV3Severity": "CRITICAL",  # Filtramos por severidad
    }

    headers = {}
    api_key = os.getenv("NVD_API_KEY")
    if api_key:
        headers["apiKey"] = api_key

    results = []

    async with httpx.AsyncClient(timeout=30) as client:
        # Primera llamada: CVEs CRITICAL
        try:
            resp = await client.get(NVD_BASE_URL, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            results += _parse_nvd_response(data, "critical")
        except Exception as e:
            print(f"[CVE Fetcher] Error fetching CRITICAL: {e}")

        # Segunda llamada: CVEs HIGH
        try:
            params["cvssV3Severity"] = "HIGH"
            resp = await client.get(NVD_BASE_URL, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            results += _parse_nvd_response(data, "high")
        except Exception as e:
            print(f"[CVE Fetcher] Error fetching HIGH: {e}")

    # Ordenar: critical primero, luego por score descendente
    results.sort(key=lambda x: (x["severity"] != "critical", -x["cvss_score"]))

    return results[:20]  # Maximo 20 CVEs para no saturar la UI


def _parse_nvd_response(data: dict, severity: str) -> list[dict]:
    """
    Extrae los campos relevantes de la respuesta cruda de la NVD API.
    La estructura de la API v2 es bastante anidada, esto la aplana.
    """
    items = []

    for vuln in data.get("vulnerabilities", []):
        cve = vuln.get("cve", {})
        cve_id = cve.get("id", "N/A")

        # Descripcion en ingles (la API devuelve multiples idiomas)
        descriptions = cve.get("descriptions", [])
        description = next(
            (d["value"] for d in descriptions if d["lang"] == "en"),
            "No description available."
        )

        # Score CVSS v3 (preferimos v3, fallback a v2)
        cvss_score = 0.0
        metrics = cve.get("metrics", {})

        if "cvssMetricV31" in metrics:
            cvss_score = metrics["cvssMetricV31"][0]["cvssData"]["baseScore"]
        elif "cvssMetricV30" in metrics:
            cvss_score = metrics["cvssMetricV30"][0]["cvssData"]["baseScore"]
        elif "cvssMetricV2" in metrics:
            cvss_score = metrics["cvssMetricV2"][0]["cvssData"]["baseScore"]

        # Fecha de publicacion
        published = cve.get("published", "")
        try:
            pub_date = datetime.fromisoformat(published.replace("Z", "+00:00"))
            pub_date_str = pub_date.strftime("%d %b %Y")
        except Exception:
            pub_date_str = published[:10] if published else "Unknown"

        # Vendors/productos afectados
        affected = _extract_affected(cve)

        # URL de referencia principal
        references = cve.get("references", [])
        ref_url = references[0]["url"] if references else f"https://nvd.nist.gov/vuln/detail/{cve_id}"

        items.append({
            "type": "cve",
            "id": cve_id,
            "title": f"{cve_id} — {affected or 'Multiple products'}",
            "severity": severity,
            "cvss_score": cvss_score,
            "description": description[:300] + "..." if len(description) > 300 else description,
            "published": pub_date_str,
            "affected": affected,
            "url": ref_url,
        })

    return items


def _extract_affected(cve: dict) -> str:
    """
    Intenta extraer el nombre del vendor/producto afectado de la configuracion CPE.
    """
    try:
        configs = cve.get("configurations", [])
        if not configs:
            return ""
        nodes = configs[0].get("nodes", [])
        if not nodes:
            return ""
        cpe_matches = nodes[0].get("cpeMatch", [])
        if not cpe_matches:
            return ""
        # CPE format: cpe:2.3:a:vendor:product:version:...
        cpe = cpe_matches[0].get("criteria", "")
        parts = cpe.split(":")
        if len(parts) >= 5:
            vendor = parts[3].replace("_", " ").title()
            product = parts[4].replace("_", " ").title()
            return f"{vendor} {product}"
    except Exception:
        pass
    return ""
