import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

type Params = Record<string, string | number | boolean | null | undefined>;

/** Thin wrapper around HttpClient that prefixes `/api` and drops empty params. */
@Injectable({ providedIn: 'root' })
export class Api {
  private http = inject(HttpClient);
  private base = '/api';

  private params(p?: Params): HttpParams {
    let hp = new HttpParams();
    for (const [k, v] of Object.entries(p ?? {})) {
      if (v !== null && v !== undefined && v !== '') hp = hp.set(k, String(v));
    }
    return hp;
  }

  get<T>(path: string, params?: Params): Observable<T> {
    return this.http.get<T>(this.base + path, { params: this.params(params) });
  }
  post<T>(path: string, body: unknown = {}): Observable<T> {
    return this.http.post<T>(this.base + path, body);
  }
  patch<T>(path: string, body: unknown): Observable<T> {
    return this.http.patch<T>(this.base + path, body);
  }
  delete<T>(path: string): Observable<T> {
    return this.http.delete<T>(this.base + path);
  }
  blob(path: string, params?: Params): Observable<Blob> {
    return this.http.get(this.base + path, { params: this.params(params), responseType: 'blob' });
  }
}

/** Extracts a human-readable message from an API error. */
export function errorMessage(err: any): string {
  const d = err?.error?.detail;
  if (typeof d === 'string') return d;
  if (Array.isArray(d) && d.length) {
    return d
      .map((e: any) => {
        const field = (e.loc ?? []).filter((x: any) => x !== 'body').join('.');
        return field ? `${field}: ${e.msg}` : e.msg;
      })
      .join('; ');
  }
  if (err?.status === 0) return 'Cannot reach the server. Check your connection.';
  return err?.message ?? 'Something went wrong';
}

export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
