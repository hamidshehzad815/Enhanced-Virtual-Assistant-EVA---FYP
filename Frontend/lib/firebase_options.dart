import 'package:firebase_core/firebase_core.dart' show FirebaseOptions;
import 'dart:io' show Platform;
import 'package:flutter/foundation.dart' show kIsWeb;

class DefaultFirebaseOptions {
  static const FirebaseOptions web = FirebaseOptions(
    apiKey: "AIzaSyCGarWqD1hYJkj_8W8lxrb5uVCYvW2pVI4",
    authDomain: "evafirebase-c92ab-10f93.firebaseapp.com",
    projectId: "evafirebase-c92ab-10f93",
    storageBucket: "evafirebase-c92ab-10f93.firebasestorage.app",
    messagingSenderId: "860559086274",
    appId: "1:860559086274:web:91f0068e8d5b5855b2615b",
    measurementId: "G-8DVJ2550GH",
  );
  static const FirebaseOptions android = FirebaseOptions(
    apiKey: "AIzaSyAwcXNMMpgCgVIqCud3Mmwva6s1Z2cz2i0", 
    appId: "1:860559086274:android:52fc4e36f4b50c4eb2615b", 
    projectId: "evafirebase-c92ab-10f93",
    storageBucket: "evafirebase-c92ab-10f93.firebasestorage.app",
    messagingSenderId: "860559086274",
    // authDomain is NOT needed for Android
  );

  static FirebaseOptions get currentPlatform {
    if (kIsWeb) return web;
    if (Platform.isAndroid) return android;
    // for iOS, add ios config later
    return web; // fallback
  }
}