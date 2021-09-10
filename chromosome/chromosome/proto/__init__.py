import os
import sys


# protoc can't generate Python files with relative imports and Python 3 doesn't
# have implicit relative imports like Python 2. This is unfortunate because we
# don't want to add service-specific absolute import paths to .proto files
# because that'll break portability, i.e. whoever uses the proto files has to
# have the exact same file structure or they need to change the imports in the
# proto files to fit their use case. We could make the imports relative by
# modifying them in the generated files but this is finicky because it adds an
# extra build step that, if skipped/fails, could leave the developer perplexed.
# So instead here we hack this proto module into the System PATH so the
# generated files' absolute(ly wrong) imports work correctly...
# Google doesn't seem interested in adding support for relative paths:
# https://github.com/protocolbuffers/protobuf/issues/1491
sys.path.append(os.path.dirname(__file__))
