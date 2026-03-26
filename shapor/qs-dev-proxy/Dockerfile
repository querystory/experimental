FROM golang:1.25-alpine AS build
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY main.go .
RUN CGO_ENABLED=0 go build -o /proxy .

FROM gcr.io/distroless/static-debian12
COPY --from=build /proxy /proxy
ENTRYPOINT ["/proxy"]
