import org.jetbrains.kotlin.gradle.dsl.JvmTarget

// Pure Kotlin/JVM module: no Android imports, so the DSP can be unit-tested on any JDK.
plugins {
    id("org.jetbrains.kotlin.jvm")
}

java {
    sourceCompatibility = JavaVersion.VERSION_17
    targetCompatibility = JavaVersion.VERSION_17
}

kotlin {
    compilerOptions {
        jvmTarget.set(JvmTarget.JVM_17)
    }
}

dependencies {
    // Test-only. JUnit 4 is EPL-1.0 and is not shipped in the app; kotlinx-serialization-json
    // (Apache-2.0) is used only to read the JSON test vectors (no compiler plugin needed for that).
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.7.3")
}

tasks.test {
    // Test vectors live outside the Android project, at <repo>/tests/vectors.
    systemProperty("qs.vectors", rootProject.projectDir.resolve("../tests/vectors").canonicalPath)
    maxHeapSize = "1g"
    testLogging {
        events("passed", "failed", "skipped")
        showStandardStreams = true
    }
}
