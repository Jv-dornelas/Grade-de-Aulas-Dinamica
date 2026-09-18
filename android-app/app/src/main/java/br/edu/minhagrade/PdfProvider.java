package br.edu.minhagrade;

import android.content.ContentProvider;
import android.content.ContentValues;
import android.database.Cursor;
import android.database.MatrixCursor;
import android.net.Uri;
import android.os.ParcelFileDescriptor;
import android.provider.OpenableColumns;
import java.io.File;
import java.io.FileNotFoundException;

/** Compartilha apenas PDFs temporários; não permite escrita nem acesso a outros arquivos. */
public class PdfProvider extends ContentProvider {
    @Override public boolean onCreate() { return true; }

    private File resolve(Uri uri) throws FileNotFoundException {
        if (!"br.edu.minhagrade.pdf".equals(uri.getAuthority()) || uri.getPathSegments().size() != 1)
            throw new FileNotFoundException();
        String name = uri.getLastPathSegment();
        if (name == null || !name.matches("grade-[a-f0-9-]+\\.pdf") || getContext() == null)
            throw new FileNotFoundException();
        File file = new File(getContext().getCacheDir(), name);
        if (!file.isFile()) throw new FileNotFoundException();
        return file;
    }

    @Override public String getType(Uri uri) { return "application/pdf"; }
    @Override public ParcelFileDescriptor openFile(Uri uri, String mode) throws FileNotFoundException {
        if (!"r".equals(mode)) throw new FileNotFoundException("Somente leitura");
        return ParcelFileDescriptor.open(resolve(uri), ParcelFileDescriptor.MODE_READ_ONLY);
    }
    @Override public Cursor query(Uri uri, String[] projection, String selection, String[] args, String order) {
        try {
            File file = resolve(uri);
            String[] columns = projection == null ? new String[]{OpenableColumns.DISPLAY_NAME, OpenableColumns.SIZE} : projection;
            MatrixCursor cursor = new MatrixCursor(columns, 1);
            Object[] values = new Object[columns.length];
            for (int i = 0; i < columns.length; i++) {
                if (OpenableColumns.DISPLAY_NAME.equals(columns[i])) values[i] = "minha-grade.pdf";
                if (OpenableColumns.SIZE.equals(columns[i])) values[i] = file.length();
            }
            cursor.addRow(values);
            return cursor;
        } catch (FileNotFoundException e) { return null; }
    }
    @Override public Uri insert(Uri uri, ContentValues values) { throw new UnsupportedOperationException(); }
    @Override public int update(Uri uri, ContentValues values, String s, String[] args) { throw new UnsupportedOperationException(); }
    @Override public int delete(Uri uri, String s, String[] args) { throw new UnsupportedOperationException(); }
}
