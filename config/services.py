from classes.services import data_service

GeckoService: data_service.GeckoService

def configure():
    import env

    GeckoService = data_service.GeckoService()