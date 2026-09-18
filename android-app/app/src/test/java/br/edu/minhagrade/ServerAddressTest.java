package br.edu.minhagrade;

import org.junit.Test;
import static org.junit.Assert.*;

public class ServerAddressTest {
    @Test public void acceptsPrivateNetworkAndPublicHttps() throws Exception {
        assertEquals("http://192.168.15.37:8000", MainActivity.normalizeServer(" http://192.168.15.37:8000/ "));
        assertEquals("http://10.0.0.1:8000", MainActivity.normalizeServer("http://10.0.0.1:8000"));
        assertEquals("http://172.16.1.10", MainActivity.normalizeServer("http://172.16.1.10"));
        assertEquals("https://grade.example.org", MainActivity.normalizeServer("https://grade.example.org/"));
    }

    @Test public void rejectsCredentialsPathsAndInsecurePublicServers() {
        for (String value : new String[]{
            "http://example.org", "http://8.8.8.8", "http://172.32.0.1",
            "http://192.168.999.1", "javascript:alert(1)", "file:///etc/passwd",
            "https://user:password@example.org", "https://example.org/mobile/",
            "https://example.org?next=foo", "https://example.org#fragment",
            "https://example.org:65536", "https://example.org:0", "192.168.15.37:8000"
        }) {
            assertThrows(value, Exception.class, () -> MainActivity.normalizeServer(value));
        }
    }
}
