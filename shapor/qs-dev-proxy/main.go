package main

import (
	"context"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strings"

	"cloud.google.com/go/storage"
)

var (
	bucket     = envOr("BUCKET", "qs-dev")
	listenAddr = ":" + envOr("PORT", "8080")
)

func envOr(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}

func main() {
	ctx := context.Background()
	client, err := storage.NewClient(ctx)
	if err != nil {
		log.Fatalf("storage client: %v", err)
	}

	http.HandleFunc("/_identity", identityHandler)
	http.HandleFunc("/", handler(client))
	log.Printf("listening on %s (bucket: %s)", listenAddr, bucket)
	log.Fatal(http.ListenAndServe(listenAddr, nil))
}

func identityHandler(w http.ResponseWriter, r *http.Request) {
	email := r.Header.Get("X-Goog-Authenticated-User-Email")
	// IAP prefixes with "accounts.google.com:" — strip it
	email = strings.TrimPrefix(email, "accounts.google.com:")
	w.Header().Set("Content-Type", "application/json")
	fmt.Fprintf(w, `{"email":%q}`, email)
}

func handler(client *storage.Client) http.HandlerFunc {
	bkt := client.Bucket(bucket)

	return func(w http.ResponseWriter, r *http.Request) {
		// Extract app name from subdomain: gartner.qs.dev → gartner
		host := r.Host
		if i := strings.Index(host, ":"); i != -1 {
			host = host[:i]
		}
		parts := strings.SplitN(host, ".", 2)
		if len(parts) < 2 || parts[0] == "" {
			http.Error(w, "invalid host", http.StatusBadRequest)
			return
		}
		app := parts[0]

		// Object path: {app}/{request_path}, default to index.html
		reqPath := strings.TrimPrefix(r.URL.Path, "/")
		if reqPath == "" || strings.HasSuffix(reqPath, "/") {
			reqPath += "index.html"
		}
		objPath := app + "/" + reqPath

		obj := bkt.Object(objPath)
		attrs, err := obj.Attrs(r.Context())
		if err == storage.ErrObjectNotExist {
			http.Error(w, "not found", http.StatusNotFound)
			return
		}
		if err != nil {
			log.Printf("attrs %s/%s: %v", bucket, objPath, err)
			http.Error(w, "internal error", http.StatusInternalServerError)
			return
		}

		w.Header().Set("Content-Type", attrs.ContentType)
		w.Header().Set("Accept-Ranges", "bytes")
		w.Header().Set("Content-Length", fmt.Sprintf("%d", attrs.Size))

		// Handle Range requests for video seeking
		rangeHeader := r.Header.Get("Range")
		if rangeHeader != "" {
			serveRange(w, r, obj, attrs, rangeHeader)
			return
		}

		reader, err := obj.NewReader(r.Context())
		if err != nil {
			log.Printf("read %s/%s: %v", bucket, objPath, err)
			http.Error(w, "internal error", http.StatusInternalServerError)
			return
		}
		defer reader.Close()
		io.Copy(w, reader)
	}
}

func serveRange(w http.ResponseWriter, r *http.Request, obj *storage.ObjectHandle, attrs *storage.ObjectAttrs, rangeHeader string) {
	var start, end int64
	end = attrs.Size - 1
	n, _ := fmt.Sscanf(strings.TrimPrefix(rangeHeader, "bytes="), "%d-%d", &start, &end)
	if n == 0 {
		http.Error(w, "bad range", http.StatusRequestedRangeNotSatisfiable)
		return
	}
	if end >= attrs.Size {
		end = attrs.Size - 1
	}
	length := end - start + 1

	reader, err := obj.NewRangeReader(r.Context(), start, length)
	if err != nil {
		log.Printf("range read: %v", err)
		http.Error(w, "internal error", http.StatusInternalServerError)
		return
	}
	defer reader.Close()

	w.Header().Set("Content-Range", fmt.Sprintf("bytes %d-%d/%d", start, end, attrs.Size))
	w.Header().Set("Content-Length", fmt.Sprintf("%d", length))
	w.Header().Set("Content-Type", attrs.ContentType)
	w.WriteHeader(http.StatusPartialContent)
	io.Copy(w, reader)
}
