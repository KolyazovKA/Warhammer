# ChromaDB runs as an embedded PersistentClient inside the backend container.
# A separate datastore container is not required.
# Data is persisted via the Docker volume mounted at /app/choma_db in the backend service.
#
# If you need a standalone ChromaDB HTTP server in the future, use the official image:
#   chromadb/chroma:latest
