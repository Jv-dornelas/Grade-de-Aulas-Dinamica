package br.edu.minhagrade;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ClipData;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.print.PrintAttributes;
import android.print.PrintManager;
import android.view.View;
import android.view.WindowInsets;
import android.webkit.CookieManager;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URI;
import java.net.URL;
import java.util.Locale;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Contêiner híbrido: telas no Django; conexão, impressão e arquivos no Android. */
public class MainActivity extends Activity {
    private static final String DEFAULT_SERVER = "http://192.168.15.37:8000";
    private static final int SAVE_PDF = 10;
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private WebView web;
    private TextView status;
    private ProgressBar progress;
    private String server;
    private File pendingPdf;
    private boolean downloading;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        server = getPreferences(MODE_PRIVATE).getString("server", DEFAULT_SERVER);
        if (state != null) {
            String savedFile = state.getString("pendingPdf");
            if (savedFile != null && savedFile.matches("grade-[a-f0-9-]+\\.pdf")) {
                File candidate = new File(getCacheDir(), savedFile);
                if (candidate.isFile()) pendingPdf = candidate;
            }
        }
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.rgb(244, 247, 245));
        root.setOnApplyWindowInsetsListener((view, insets) -> {
            if (android.os.Build.VERSION.SDK_INT >= 30) {
                android.graphics.Insets bars = insets.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.ime());
                view.setPadding(bars.left, bars.top, bars.right, bars.bottom);
            } else {
                view.setPadding(insets.getSystemWindowInsetLeft(), insets.getSystemWindowInsetTop(),
                    insets.getSystemWindowInsetRight(), insets.getSystemWindowInsetBottom());
            }
            return insets;
        });
        LinearLayout toolbar = new LinearLayout(this);
        toolbar.setPadding(dp(12), dp(4), dp(12), dp(4));
        toolbar.setGravity(android.view.Gravity.CENTER_VERTICAL);
        status = new TextView(this);
        status.setText("Minha Grade · Android");
        status.setTextColor(Color.rgb(22, 78, 71));
        toolbar.addView(status, new LinearLayout.LayoutParams(0, -2, 1));
        Button options = new Button(this);
        options.setText("Opções");
        options.setOnClickListener(v -> showOptions());
        toolbar.addView(options);
        root.addView(toolbar);
        progress = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        root.addView(progress, new LinearLayout.LayoutParams(-1, dp(3)));
        web = new WebView(this);
        root.addView(web, new LinearLayout.LayoutParams(-1, 0, 1));
        setContentView(root);
        configureWeb();
        if (!getPreferences(MODE_PRIVATE).getBoolean("configured", false)) {
            configureServer();
        } else {
            web.loadUrl(server + "/mobile/");
        }
    }

    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }

    @android.annotation.SuppressLint("SetJavaScriptEnabled")
    private void configureWeb() {
        WebSettings settings = web.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        settings.setCacheMode(WebSettings.LOAD_NO_CACHE);
        settings.setUserAgentString(settings.getUserAgentString() + " MinhaGradeAndroid/1.0");
        CookieManager.getInstance().setAcceptCookie(true);
        CookieManager.getInstance().setAcceptThirdPartyCookies(web, false);
        web.setWebChromeClient(new WebChromeClient() {
            @Override public void onProgressChanged(WebView view, int value) {
                progress.setProgress(value);
                progress.setVisibility(value == 100 ? View.GONE : View.VISIBLE);
            }
        });
        web.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                if ("minhagrade".equals(uri.getScheme())) {
                    if (request.isForMainFrame() && isMobileUrl(web.getUrl()) && "print".equals(uri.getHost())) printPage();
                    return true;
                }
                if (!isMobileUrl(uri.toString())) {
                    toast("Use este aplicativo apenas para consultar sua grade.");
                    return true;
                }
                if ("/mobile/grade.pdf".equals(uri.getPath())) {
                    if (request.isForMainFrame()) downloadPdf(uri.toString());
                    return true;
                }
                return false;
            }
            @Override public void onPageStarted(WebView view, String url, android.graphics.Bitmap icon) {
                if (!isMobileUrl(url)) { view.stopLoading(); return; }
                status.setText("Conectando…");
            }
            @Override public void onPageFinished(WebView view, String url) {
                if (!isMobileUrl(url)) return;
                status.setText("Minha Grade · Android");
                CookieManager.getInstance().flush();
            }
            @Override public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (!request.isForMainFrame()) return;
                status.setText("Sem conexão com o servidor");
                new AlertDialog.Builder(MainActivity.this).setTitle("Não foi possível conectar")
                    .setMessage("Confira se o computador está ligado, com o Docker rodando, e se ambos estão na mesma rede. Servidor: " + server)
                    .setPositiveButton("Tentar novamente", (d, w) -> web.loadUrl(server + "/mobile/"))
                    .setNeutralButton("Trocar servidor", (d, w) -> configureServer())
                    .setNegativeButton("Fechar", null).show();
            }
            // Erros de certificado usam o comportamento padrão: cancelar, nunca ignorar.
        });
        web.setDownloadListener((url, agent, disposition, mime, length) -> downloadPdf(url));
    }

    private boolean isMobileUrl(String value) {
        if (value == null) return false;
        try {
            URI target = new URI(value);
            URI origin = new URI(server);
            return origin.getScheme().equalsIgnoreCase(target.getScheme())
                && origin.getHost().equalsIgnoreCase(target.getHost())
                && effectivePort(origin) == effectivePort(target)
                && target.getRawUserInfo() == null
                && target.getPath() != null && target.getPath().startsWith("/mobile/");
        } catch (Exception e) { return false; }
    }

    private static int effectivePort(URI uri) {
        return uri.getPort() >= 0 ? uri.getPort() : ("https".equalsIgnoreCase(uri.getScheme()) ? 443 : 80);
    }

    static String normalizeServer(String input) throws Exception {
        URI uri = new URI(input.trim());
        String scheme = uri.getScheme() == null ? "" : uri.getScheme().toLowerCase(Locale.ROOT);
        String host = uri.getHost();
        if (!(scheme.equals("http") || scheme.equals("https")) || host == null
            || uri.getRawUserInfo() != null || uri.getQuery() != null || uri.getFragment() != null
            || (uri.getPort() != -1 && (uri.getPort() < 1 || uri.getPort() > 65535))
            || !(uri.getPath().isEmpty() || uri.getPath().equals("/"))) {
            throw new IllegalArgumentException("Informe apenas o servidor, por exemplo http://192.168.15.37:8000");
        }
        if (scheme.equals("http") && !isPrivateAddress(host)) {
            throw new IllegalArgumentException("HTTP é permitido apenas para IPs da rede local. Para um servidor público, use HTTPS.");
        }
        return new URI(scheme, null, host, uri.getPort(), null, null, null).toString();
    }

    private static boolean isPrivateAddress(String host) {
        String[] parts = host.split("\\.");
        if (parts.length != 4) return false;
        int[] bytes = new int[4];
        for (int i = 0; i < 4; i++) {
            if (!parts[i].matches("[0-9]{1,3}")) return false;
            bytes[i] = Integer.parseInt(parts[i]);
            if (bytes[i] > 255) return false;
        }
        return bytes[0] == 10 || (bytes[0] == 192 && bytes[1] == 168)
            || (bytes[0] == 172 && bytes[1] >= 16 && bytes[1] <= 31);
    }

    private void configureServer() {
        EditText input = new EditText(this);
        input.setSingleLine(true);
        input.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_VARIATION_URI);
        input.setText(server);
        input.setSelectAllOnFocus(true);
        AlertDialog dialog = new AlertDialog.Builder(this).setTitle("Conectar ao computador")
            .setMessage("Digite o endereço do servidor, sem /mobile/. Use a mesma rede Wi-Fi do computador.")
            .setView(input).setPositiveButton("Conectar", null).setNegativeButton("Cancelar", null).create();
        dialog.setOnShowListener(d -> dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v -> {
            try {
                String selected = normalizeServer(input.getText().toString());
                boolean changed = !selected.equals(server);
                server = selected;
                getPreferences(MODE_PRIVATE).edit().putString("server", server).putBoolean("configured", true).apply();
                web.stopLoading();
                web.clearHistory();
                dialog.dismiss();
                if (changed) {
                    CookieManager.getInstance().removeAllCookies(done -> {
                        CookieManager.getInstance().flush();
                        web.loadUrl(server + "/mobile/");
                    });
                } else web.loadUrl(server + "/mobile/");
            } catch (Exception e) { input.setError(e.getMessage()); }
        }));
        dialog.show();
    }

    private void showOptions() {
        new AlertDialog.Builder(this).setTitle("Minha Grade")
            .setItems(new String[]{"Atualizar grade", "Baixar / compartilhar PDF", "Imprimir", "Trocar servidor", "Sobre o aplicativo"}, (d, option) -> {
                if (option == 0) web.loadUrl(server + "/mobile/");
                if (option == 1) {
                    if (!isSchedulePage()) { toast("Entre como professor e abra sua grade primeiro."); return; }
                    Uri current = Uri.parse(web.getUrl());
                    Uri.Builder pdf = Uri.parse(server + "/mobile/grade.pdf").buildUpon();
                    String week = current.getQueryParameter("semana");
                    if (week != null) pdf.appendQueryParameter("semana", week);
                    downloadPdf(pdf.build().toString());
                }
                if (option == 2) printPage();
                if (option == 3) configureServer();
                if (option == 4) new AlertDialog.Builder(this).setTitle("Minha Grade · 1.0 demo")
                    .setMessage("Aplicativo híbrido para consulta de horários de professores. Interface Django em WebView, com arquivos, compartilhamento e impressão integrados ao Android.\n\nServidor: " + server + "\n\nO computador precisa estar ligado. PDFs baixados são cópias e não atualizam automaticamente.")
                    .setPositiveButton("Entendi", null).show();
            }).show();
    }

    private boolean isSchedulePage() {
        return isMobileUrl(web.getUrl()) && "/mobile/".equals(Uri.parse(web.getUrl()).getPath());
    }

    private void printPage() {
        if (!isSchedulePage()) { toast("Abra sua grade antes de imprimir."); return; }
        PrintManager manager = (PrintManager) getSystemService(PRINT_SERVICE);
        if (manager != null) manager.print("Minha Grade", web.createPrintDocumentAdapter("Minha Grade"),
            new PrintAttributes.Builder().setMediaSize(PrintAttributes.MediaSize.ISO_A4).build());
    }

    private void downloadPdf(String url) {
        if (!isMobileUrl(url) || !"/mobile/grade.pdf".equals(Uri.parse(url).getPath())) {
            toast("Este arquivo não pertence à sua grade."); return;
        }
        if (downloading) { toast("Aguarde o download atual."); return; }
        downloading = true;
        String cookies = CookieManager.getInstance().getCookie(url);
        toast("Preparando PDF…");
        worker.execute(() -> {
            File pdf = new File(getCacheDir(), "grade-" + UUID.randomUUID() + ".pdf");
            HttpURLConnection connection = null;
            try {
                connection = (HttpURLConnection) new URL(url).openConnection();
                connection.setInstanceFollowRedirects(false);
                connection.setConnectTimeout(15000);
                connection.setReadTimeout(20000);
                if (cookies != null) connection.setRequestProperty("Cookie", cookies);
                if (connection.getResponseCode() != 200 || connection.getContentType() == null
                    || !connection.getContentType().toLowerCase(Locale.ROOT).startsWith("application/pdf")) {
                    throw new IllegalStateException("Entre como professor novamente e tente baixar a grade.");
                }
                try (InputStream in = connection.getInputStream(); OutputStream out = new FileOutputStream(pdf)) {
                    byte[] buffer = new byte[8192];
                    int read, total = 0;
                    while ((read = in.read(buffer)) != -1) {
                        total += read;
                        if (total > 10 * 1024 * 1024) throw new IllegalStateException("PDF maior que o limite de 10 MB.");
                        out.write(buffer, 0, read);
                    }
                }
                try (InputStream input = new FileInputStream(pdf)) {
                    byte[] magic = new byte[5];
                    if (input.read(magic) != 5 || !"%PDF-".equals(new String(magic, java.nio.charset.StandardCharsets.US_ASCII)))
                        throw new IllegalStateException("O servidor não retornou um PDF válido.");
                }
                runOnUiThread(() -> {
                    downloading = false;
                    if (isFinishing() || isDestroyed()) return;
                    pendingPdf = pdf;
                    new AlertDialog.Builder(this).setTitle("PDF pronto")
                        .setItems(new String[]{"Salvar nos arquivos do celular", "Compartilhar PDF"}, (d, action) -> {
                            if (action == 0) {
                                Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT).setType("application/pdf")
                                    .addCategory(Intent.CATEGORY_OPENABLE).putExtra(Intent.EXTRA_TITLE, "minha-grade.pdf");
                                startActivityForResult(intent, SAVE_PDF);
                            } else sharePdf(pdf);
                        }).show();
                });
            } catch (Exception e) {
                // Remove somente o arquivo temporário criado por esta operação.
                if (pdf.exists()) pdf.delete();
                runOnUiThread(() -> { downloading = false; toast("Não foi possível baixar: " + e.getMessage()); });
            } finally { if (connection != null) connection.disconnect(); }
        });
    }

    private void sharePdf(File pdf) {
        Uri uri = Uri.parse("content://br.edu.minhagrade.pdf/" + pdf.getName());
        Intent intent = new Intent(Intent.ACTION_SEND).setType("application/pdf")
            .putExtra(Intent.EXTRA_STREAM, uri).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        intent.setClipData(ClipData.newRawUri("Minha Grade", uri));
        startActivity(Intent.createChooser(intent, "Compartilhar grade"));
    }

    @Override protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request, result, data);
        if (request != SAVE_PDF || result != RESULT_OK || data == null || data.getData() == null || pendingPdf == null) return;
        Uri destination = data.getData();
        File source = pendingPdf;
        worker.execute(() -> {
            try (InputStream in = new FileInputStream(source); OutputStream out = getContentResolver().openOutputStream(destination)) {
                if (out == null) throw new IllegalStateException("Destino indisponível");
                byte[] buffer = new byte[8192];
                int count;
                while ((count = in.read(buffer)) != -1) out.write(buffer, 0, count);
                runOnUiThread(() -> toast("PDF salvo nos arquivos do celular."));
            } catch (Exception e) { runOnUiThread(() -> toast("Não foi possível salvar o PDF.")); }
        });
    }

    @Override protected void onSaveInstanceState(Bundle out) {
        if (pendingPdf != null) out.putString("pendingPdf", pendingPdf.getName());
        super.onSaveInstanceState(out);
    }
    @Override public void onBackPressed() {
        if (web.canGoBack()) web.goBack(); else super.onBackPressed();
    }
    @Override protected void onDestroy() {
        web.destroy();
        worker.shutdown();
        super.onDestroy();
    }
    private void toast(String message) {
        if (!isFinishing() && !isDestroyed()) Toast.makeText(this, message, Toast.LENGTH_LONG).show();
    }
}
