from nautobot.extras.jobs import Job, StringVar, ObjectVar, MultiObjectVar, TextVar
from nautobot.dcim.models import Location, Device, DeviceType, Manufacturer
from nautobot.extras.models import CustomField, CustomFieldValue, Role, Status
from nautobot.core.exceptions import ValidationError

class CreateLocationSiteDevice(Job):
    class Meta:
        name = "Choose Location and Device"
        description = "Choose a location and create a device with optional custom fields"

    location = ObjectVar(
        model=Location,
        display_field="name",
        required=True,
        description="Select a location",
    )

    device_name = StringVar(
        description="Enter the device name",
        required=True
    )

    custom_fields = TextVar(
        description="Optional custom fields in JSON format",
        required=False
    )
    # data does not exist in v2. Call out the data fields explicitly
    def run(self, **data):
        location = data['location']
        device_name = data['device_name']
        custom_fields_data = data.get('custom_fields', {})

        # Create the device
        try:
            manufacturer = Manufacturer.objects.first()  # Assuming at least one manufacturer exists
            device_type = DeviceType.objects.first()  # Assuming at least one device type exists
            device_role = Role.objects.first()  # Assuming at least one device role exists
            status = Status.objects.first() 

            device, created = Device.objects.get_or_create(
                name=device_name,
                location=location,
                status=status,
                device_type=device_type,
                device_role=device_role
            )
            if created:
                self.logger.info(f"Created device '{device_name}' at site '{location}'")
            else:
                self.logger.info(f"Device '{device_name}' already exists at site '{location}'")

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
                    self.logger.info(f"Applied custom fields to device '{device_name}'")
                except Exception as e:
                    self.logger.warning(f"Failed to apply custom fields: {str(e)}")
            else:
                self.logger.info("No custom fields provided")
        except Exception as e:
            self.logger.error(f"Failed to create device: {str(e)}")
            raise ValidationError(f"Failed to create device: {str(e)}")

        return "Job completed successfully"

# Register the job
#jobs = [CreateLocationSiteDevice]
#register_jobs(*jobs)
