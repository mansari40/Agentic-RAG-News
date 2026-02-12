class BaselineRAGException(Exception):
    pass


class ExternalAPIError(BaselineRAGException):
    pass


class StorageLayerError(BaselineRAGException):
    pass


class EmbeddingServiceError(BaselineRAGException):
    pass
