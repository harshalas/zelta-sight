module.exports = {
  expo: {
    name: "frontend",
    slug: "frontend",
    version: "1.0.0",
    orientation: "portrait",
    updates: {
      enabled: false,
      checkAutomatically: "NEVER"
    },
    icon: "./assets/icon.png",
    icon: "./assets/icon.png",
    userInterfaceStyle: "light",
    ios: {
      supportsTablet: true
    },
    android: {
      adaptiveIcon: {
        backgroundColor: "#E6F4FE",
        foregroundImage: "./assets/android-icon-foreground.png",
        backgroundImage: "./assets/android-icon-background.png",
        monochromeImage: "./assets/android-icon-monochrome.png"
      },
      package: "com.anonymous.frontend"
    },
    web: {
      favicon: "./assets/favicon.png"
    },
    // This extra section dynamically reads from your local .env file!
    extra: {
      eas: {
        projectId: "6bf8ecac-143d-445b-bd34-620b4952b7b5"
      }
    }
  }
};