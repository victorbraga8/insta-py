def set_geolocation(
    driver, latitude: float = -22.8268, longitude: float = -43.0634, accuracy: int = 100
):
    driver.execute_cdp_cmd(
        "Browser.grantPermissions",
        {"origin": "https://www.instagram.com", "permissions": ["geolocation"]},
    )
    driver.execute_cdp_cmd(
        "Emulation.setGeolocationOverride",
        {"latitude": latitude, "longitude": longitude, "accuracy": accuracy},
    )
