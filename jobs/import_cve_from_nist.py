from datetime import datetime
import requests
from nautobot.apps.jobs import Job, StringVar, register_jobs
from nautobot_device_lifecycle_mgmt.models import CVELCM

class ImportCVEFromNIST(Job):
    """Job to import CVEs from NIST NVD into Nautobot's CVE model."""
    
    published_after = StringVar(
        label="CVEs Published After",
        description="Fetch CVEs published after this date (YYYY-MM-DD).",
        default="1970-01-01",
        required=False
    )

    def fetch_cve_data(self, published_after):
        """Fetch CVE data from the NIST NVD JSON feed."""
        url = "https://nvd.nist.gov/vuln/search/results?form_type=Basic&results_type=overview&search_type=last3months&isCpeNameSearch=false"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json().get("result", {}).get("CVE_Items", [])
        else:
            self.logger.error("Failed to fetch CVE data: %s", response.status_code)
            return []

    def run(self, published_after):
        published_after = published_after or "1970-01-01"
        cve_items = self.fetch_cve_data(published_after)
        
        for cve_item in cve_items:
            cve_data = {
                "name": cve_item["cve"]["CVE_data_meta"]["ID"],
                "description": cve_item["cve"]["description"]["description_data"][0]["value"],
                "publish_date": datetime.strptime(cve_item["publishedDate"], "%Y-%m-%dT%H:%MZ"),
                "link": f"https://nvd.nist.gov/vuln/detail/{cve_item['cve']['CVE_data_meta']['ID']}",
                "severity": cve_item["impact"]["baseMetricV3"]["cvssV3"]["baseSeverity"],
                "cvss_base_score": cve_item["impact"]["baseMetricV3"]["cvssV3"]["baseScore"],
            }
            
            CVELCM.objects.update_or_create(
                name=cve_data["name"],
                defaults=cve_data
            )
            self.logger.info("Processed CVE: %s", cve_data["name"])

register_jobs(ImportCVEFromNIST)
