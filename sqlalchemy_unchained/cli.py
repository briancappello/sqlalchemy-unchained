"""
Override the alembic command to customize the templates directory
"""
import os

from alembic.config import Config as BaseConfig, CommandLine as BaseCommandLine


class Config(BaseConfig):
    def get_template_directory(self):
        return os.path.join(
            os.path.abspath(os.path.dirname(os.path.dirname(__file__))),
            'alembic_templates')


class CommandLine(BaseCommandLine):
    def main(self, argv=None):
        options = self.parser.parse_args(argv)
        if not hasattr(options, "cmd"):
            # see http://bugs.python.org/issue9253, argparse
            # behavior changed incompatibly in py3.3
            self.parser.error("too few arguments")
        else:
            cfg = Config(file_=options.config,
                         ini_section=options.name, cmd_opts=options)
            self.run_cmd(cfg, options)


def main(argv=None, prog=None, **kwargs):
    CommandLine(prog=prog).main(argv=argv)


if __name__ == '__main__':
    main()
