from nautobot.extras.jobs import Job, StringVar, ObjectVar, MultiObjectVar, TextVar
from nautobot.dcim.models import Location, Site, Device, DeviceType, DeviceRole, Manufacturer
from nautobot.extras.models import CustomField, CustomFieldValue
from nautobot.core.exceptions import ValidationError
from nautobot.apps.jobs import Job, register_jobs

class CreateLocationSiteDevice(Job):
    class Meta:
        name = "Create Location, Site, and Device"
        description = "Create a location, site, and device with optional custom fields"

    location = ObjectVar(
        model=Location,
        display_field="name",
        required=True,
        description="Select a location",
    )

    site_name = StringVar(
        description="Enter the site name",
        required=True
    )

    device_name = StringVar(
        description="Enter the device name",
        required=True
    )

    custom_fields = TextVar(
        description="Optional custom fields in JSON format",
        required=False
    )

    def run(self, data, commit):
        location = data['location']
        site_name = data['site_name']
        device_name = data['device_name']
        custom_fields_data = data.get('custom_fields', {})

        # Create the site
        site, created = Site.objects.get_or_create(
            name=site_name,
            defaults={'location': location}
        )
        if created:
            self.log_info(f"Created site '{site_name}' in location '{location.name}'")
        else:
            self.log_info(f"Site '{site_name}' already exists in location '{location.name}'")

        # Create the device
        try:
            manufacturer = Manufacturer.objects.first()  # Assuming at least one manufacturer exists
            device_type = DeviceType.objects.first()  # Assuming at least one device type exists
            device_role = DeviceRole.objects.first()  # Assuming at least one device role exists

            device, created = Device.objects.get_or_create(
                name=device_name,
                site=site,
                device_type=device_type,
                device_role=device_role
            )
            if created:
                self.log_info(f"Created device '{device_name}' at site '{site_name}'")
            else:
                self.log_info(f"Device '{device_name}' already exists at site '{site_name}'")

            # Apply custom fields if provided
            if custom_fields_data:
                try:
                    custom_fields_dict = eval(custom_fields_data)
                    for field_name, value in custom_fields_dict.items():
                        custom_field = CustomField.objects.get(name=field_name)
                        CustomFieldValue.objects.update_or_create(
                            obj=device,
                            field=custom_field,
                            defaults={'value': value}
                        )
                    self.log_info(f"Applied custom fields to device '{device_name}'")
                except Exception as e:
                    self.log_warning(f"Failed to apply custom fields: {str(e)}")
            else:
                self.log_info("No custom fields provided")
        except Exception as e:
            self.log_error(f"Failed to create device: {str(e)}")
            raise ValidationError(f"Failed to create device: {str(e)}")

        return "Job completed successfully"

# Register the job
register_jobs(CreateLocationSiteDevice)
