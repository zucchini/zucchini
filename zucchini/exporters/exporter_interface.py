from abc import ABCMeta, abstractmethod


class ExporterInterface:
    __metaclass__ = ABCMeta

    # The class needs an init method that will take in all of its desired
    # options from the command line, in order.

    @abstractmethod
    def export(self, submission):
        """This method should take in a Submission object and export its
        grading to whatever export it's doing.
        For example, if we're exporting to CSV, the Exporter object should
        have the CSV file as an attribute, and
        this function should write one submission's grade to the CSV file."""
        pass

    def __enter__(self):
        """This method allows us to use the with keyword for our exporter."""
        return self

    def __exit__(self, *args):
        """This method will be used to close any open files etc. at the end of
        the exporting procedure.
        It is automatically called when the with block terminates. Close any
        files and complete any submissions here."""
        return
