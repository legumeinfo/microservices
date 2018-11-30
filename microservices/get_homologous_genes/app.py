import get_homologous_genes.api as api
from core.web_app import WebApp


# the web application
app = WebApp([api.route])


if __name__ == '__main__':
  app.run()
