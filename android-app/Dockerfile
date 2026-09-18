FROM gradle:8.11.1-jdk21
USER root
ARG ACCEPT_ANDROID_SDK_LICENSES=false
RUN test "$ACCEPT_ANDROID_SDK_LICENSES" = true || (echo 'Aceite explicitamente a licença do SDK antes de compilar.' && exit 1)
ENV ANDROID_HOME=/opt/android-sdk
ENV ANDROID_SDK_ROOT=/opt/android-sdk
RUN mkdir -p /opt/android-sdk/cmdline-tools \
    && curl -fL --retry 3 https://dl.google.com/android/repository/commandlinetools-linux-15859902_latest.zip -o /tmp/android-tools.zip \
    && echo '4e4c464f145a7512b57d088ac6c278c03c9eea610886b35a5e0804e74eedf583  /tmp/android-tools.zip' | sha256sum -c - \
    && unzip -q /tmp/android-tools.zip -d /opt/android-sdk/cmdline-tools \
    && mv /opt/android-sdk/cmdline-tools/cmdline-tools /opt/android-sdk/cmdline-tools/latest
ENV PATH="/opt/android-sdk/cmdline-tools/latest/bin:/opt/android-sdk/platform-tools:${PATH}"
RUN yes | sdkmanager --licenses > /tmp/android-licenses.log \
    && sdkmanager 'platforms;android-35' 'build-tools;35.0.0' 'platform-tools'
WORKDIR /workspace
CMD ["gradle", "--no-daemon", "assembleDebug", "testDebugUnitTest", "lintDebug"]
