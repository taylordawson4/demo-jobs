import json

from nautobot.extras.jobs import Job, StringVar, ObjectVar, MultiObjectVar, TextVar
from nautobot.dcim.models import Location, Device, DeviceType, Manufacturer
from nautobot.extras.models import CustomField, Role, Status
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from django.contrib.contenttypes.models import ContentType

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
            role = Role.objects.first()  # Assuming at least one device role exists
            status = Status.objects.first() 

            device, created = Device.objects.get_or_create(
                name=device_name,
                location=location,
                status=status,
                device_type=device_type,
                role=role
            )
            if created:
                self.logger.info(f"Created device '{device_name}' at site '{location}'")
            else:
                self.logger.info(f"Device '{device_name}' already exists at site '{location}'")

            # Apply custom fields if provided
            # if custom_fields_data:
            #     try:
            #         ct_device = ContentType.objects.get_for_model(Device)
            #         for custom_field in eval(custom_fields_data):
            #             cf, _ = CustomField.objects.get_or_create(label=custom_field,key=slugify(custom_field))
            #             cf.content_types.add(ct_device)
            #         self.logger.info(f"Applied custom fields to device '{device_name}'")
            #     except Exception as e:
            #         self.logger.warning(f"Failed to apply custom fields: {str(e)}")
            # else:
            #     self.logger.info("No custom fields provided")
            if custom_fields_data:
                try:
                    ct_device = ContentType.objects.get_for_model(Device)
                    custom_fields = json.loads(custom_fields_data)
                    for field_name in custom_fields:
                        # Create or get the custom field
                        cf, created = CustomField.objects.get_or_create(
                            label=field_name,
                            key=slugify(field_name),
                            defaults={'type': 'text'}  # assuming type is 'text', adjust if needed
                        )
                        # Associate custom field with the Device content type
                        cf.content_types.add(ct_device)
                        cf.save()  # Save after modifying the content_types
            
                        # Set the custom field value for the device
                        device.custom_field_data[cf.key] = "default_value"
                    device.save()
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
