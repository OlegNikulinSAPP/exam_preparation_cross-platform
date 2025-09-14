[app]
title = Exam App
package.name = examapp
package.domain = org.exam
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 0.1
requirements = python3, kivy
orientation = portrait

[buildozer]
log_level = 2
warn_on_root = 1

# Android specific
android.api = 30
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True
android.verbose = True
android.accept_sdk_license = True

android.gradle_options = -Xmx2048m -XX:MaxPermSize=512m
android.maven_repositories = https://maven.aliyun.com/repository/public, https://maven.google.com, https://jitpack.io
android.gradle_version = 7.5
android.android_gradle_plugin_version = 7.4.2
