"""
THIS JOB IS ONLY INTENDED TO BE RUN IN THE NAUTOBOT CLOUD INSTANCE WITH Nautobot Sandbox DATA

Job accesses NIST CVE database to get CVEs for a specific vendor/software combo.
Job then creates CVE objects and the Relationship Association between the CVE and the specified Software
"""

import requests
from datetime import date

from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, transaction

from nautobot.apps.jobs import Job, register_jobs, StringVar, BooleanVar, ObjectVar, ChoiceVar, JobButtonReceiver
from nautobot.extras.models import Relationship, RelationshipAssociation
from nautobot.dcim.models import Manufacturer

from nautobot_device_lifecycle_mgmt.models import (
    CVELCM,
    SoftwareLCM,
)

name = "Get NIST CVEs"  # pylint: disable=invalid-name

class GetNistCVESMixin:
    def get_cves(self, **data):
        self.logger.info ("data = {0} ".format(data)) # debug
        
        obj = data['software']

        software_ver = obj.version
        manufacturer = obj.device_platform.manufacturer.name.lower()
        os = obj.device_platform.napalm_driver

        selected_software = {'platform': manufacturer,
                             'version': software_ver, 'os': os}

        self.logger.info("selected_software is: {}".format(selected_software))

        # Looks for CVEs for selected platform, version, and os
        cve_url = "https://services.nvd.nist.gov/rest/json/cves/2.0?cpeName=cpe:2.3:o:{}:{}:{}:*:*:*:*:*:*:*".format(
                    selected_software['platform'].lower(),
                    selected_software['os'].lower(),
                    selected_software['version'].lower())
        cve_response = requests.request("GET", cve_url)
        cves = cve_response.json()['vulnerabilities']
        self.logger.info ("Found {0} CVEs at {1}".format(len(cves), "NIST"))

        # This will hold data about the new CVEs created; will be used in creating RelationshipAssociation with
        # specified Software
        new_cves = []

        # Parse the response, draw out info needed to create CVEs, then create CVEs
        for cve in cves:
            cve_id = cve['cve']['id']
            cve_pub_date = date.fromisoformat(cve['cve']['published'].split('T')[0])
            cve_url = cve['cve']['references'][0]['url']
            cve_description = cve['cve']['descriptions'][0]['value'][:254]
            # Account for some discrepancies in how the data returned from NIST is structured
            try:
                cve_severity = cve['cve']['metrics']['cvssMetricV31'][0]['cvssData']['baseSeverity'].capitalize()
            except KeyError:
                cve_severity = cve['cve']['metrics']['cvssMetricV2'][0]['baseSeverity'].capitalize()
            try:
                cve_base_score = cve['cve']['metrics']['cvssMetricV31'][0]['cvssData']['baseScore']
            except KeyError:
                cve_base_score = cve['cve']['metrics']['cvssMetricV2'][0]['cvssData']['baseScore']
            # End of the data structure discrepancy handling

            # Data used to create a new CVE
            cve_data = {
                "name": cve_id,
                "published_date": cve_pub_date,
                "link": cve_url,
                "description": cve_description,
                "severity": cve_severity,
                "cvss": cve_base_score,
            }

            self.logger.info("Creating new CVE with data {}".format(cve_data))

            # Add newly created CVE number and id to a list
            add_cve, _ = CVELCM.objects.get_or_create(**cve_data)
            # get_or_create returns a tuple of the object and a Boolean.
            # The Boolean is if it was just created or not. In this case you don't really care if it exists already or
            # if it was created, so setting the value to _ is like telling it that you know there's a return value
            # but you don't need it.

            new_cves.append(add_cve)
        self.logger.info("new_cves = {}".format(new_cves))


        # Get the id for the selected software relevant to the CVEs
        if len(SoftwareLCM.objects.filter(version=selected_software['version'])) > 0:
            self.logger.info("Creating Software to CVE relationships")
                          
            software_object = SoftwareLCM.objects.filter(version=selected_software['version'])[0]

            for cve in new_cves:
                cve.affected_softwares.add(software_object)


class DeployConfigPlanJobButtonReceiver(JobButtonReceiver, GetNistCVESMixin):
    """Job button to get CVEs from NIST for a Software object."""

    class Meta:
        """Meta object boilerplate for config plan deployment job button."""

        name = "Get CVEs (Job Button Receiver)"
        has_sensitive_variables = False

    def receive_job_button(self, obj):
        """Run config plan deployment process."""
        self.logger.info("Starting CVE retrieval job.")
        software_ver = obj.version
        manufacturer = obj.device_platform.manufacturer.name.lower()
        os = obj.device_platform.napalm_driver
        self.logger.info("software ver = {}; manufacturer = {}; os = {}".format(software_ver, manufacturer, os))
        job_data = {'software': obj}

        # Create an instance of the class to run
        # get_cve_job = GetNistCves()
        # get_cve_job.run(data=job_data)

        # GetNistCves().run.__func__(self, job_data)
        self.get_cves(**job_data)

class GetNistCves(Job, GetNistCVESMixin):

    # Form to select the software to be queried
    # This data will be accessed via data['<fieldname>'](.<attribute>) in the code below
    software = ObjectVar(
        model=SoftwareLCM,
        query_params={
            "version": ["4.24.8M", "4.26.4M", "16.9.1"]
        },
        required=True
    )

    def run(self, **data):
        self.get_cves(**data)

register_jobs(GetNistCves)
register_jobs(DeployConfigPlanJobButtonReceiver)
