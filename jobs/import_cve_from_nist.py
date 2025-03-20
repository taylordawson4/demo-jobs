from nautobot.apps.jobs import Job, StringVar, IntegerVar, register_jobs

class UserInputJob(Job):
    """A job that demonstrates the use of user input."""

    class Meta:
        name = "User Input Job"
        description = "Job to demonstrate user inputs and their handling."
        approval_required = False  # Set to True if you want the job execution to require approval

    # Define input variables
    user_name = StringVar(description="Please enter your name")
    user_age = IntegerVar(description="Please enter your age")

    def run(self, *, user_name, user_age):
        self.logger.info("User Name: %s", user_name)
        self.logger.info("User Age: %d", user_age)
        
        if user_age < 18:
            self.logger.warning("Note: User is under 18")
        else:
            self.logger.info("User is an adult.")

register_jobs(UserInputJob)
