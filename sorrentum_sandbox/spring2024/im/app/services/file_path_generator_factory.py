"""
Produce FilePathGenerator objects.

Import as:

import im.app.services.file_path_generator_factory as imasfpgefa
"""

import im.common.data.load.file_path_generator as imcdlfpage


class FilePathGeneratorFactory:
    @classmethod
    def get_file_path_generator(
        cls, provider: str
    ) -> imcdlfpage.FilePathGenerator:
        """
        Get file path generator for a provider.

        :param provider: provider (kibot, ...)
        :raises ValueError: if FilePathGenerator is not implemented for provider
        """
        file_path_generator: imcdlfpage.FilePathGenerator
        if provider == "kibot":
            import im.kibot.data.load.kibot_file_path_generator as imkdlkfpge

            file_path_generator = imkdlkfpge.KibotFilePathGenerator()
        elif provider == "ib":
            import im.ib.data.load.ib_file_path_generator as imidlifpge

            file_path_generator = imidlifpge.IbFilePathGenerator()
        else:
            raise ValueError(
                "FilePathGenerator for provider '%s' is not implemented"
                % provider
            )
        return file_path_generator
