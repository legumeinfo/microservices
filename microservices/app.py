from core.web_app import WebApp
import compute_syntenic_blocks.api as computeSyntenicBlocksApi
import find_similar_tracks.api as findSimilarTracksApi
import genes_to_tracks.api as genesToTracksApi
import get_chromosome.api as getChromosomeApi
import get_homologous_genes.api as getHomologousGenesApi
import get_family_genes.api as getFamilyGenesApi


# the web application
routes = [
  computeSyntenicBlocksApi.route,
  findSimilarTracksApi.route,
  genesToTracksApi.route,
  getChromosomeApi.route,
  getHomologousGenesApi.route,
  getFamilyGenesApi.route,
]
app = WebApp(routes)


if __name__ == '__main__':
  app.run()
