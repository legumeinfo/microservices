import get_family_genes.api as api
from core.web_app import WebApp


app = WebApp([api.route])


if __name__ == '__main__':
  app.run()
