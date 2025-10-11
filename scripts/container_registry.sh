#!/bin/bash

# SyferStack V2 Container Registry and Deployment System
# Builds, tags, and pushes Docker images to GitHub Container Registry (GHCR)

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REGISTRY="ghcr.io"
NAMESPACE="otiseduncan"
PROJECT_NAME="syferstackv2"

# Image names
BACKEND_IMAGE="$REGISTRY/$NAMESPACE/$PROJECT_NAME/backend"
FRONTEND_IMAGE="$REGISTRY/$NAMESPACE/$PROJECT_NAME/frontend"

# Version management
VERSION_FILE="$PROJECT_ROOT/VERSION"
DEFAULT_VERSION="1.0.0"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to get current version
get_version() {
    if [ -f "$VERSION_FILE" ]; then
        cat "$VERSION_FILE"
    else
        echo "$DEFAULT_VERSION"
    fi
}

# Function to update version
update_version() {
    local version_type="${1:-patch}"
    local current_version=$(get_version)
    
    # Parse version components
    IFS='.' read -r major minor patch <<< "$current_version"
    
    case "$version_type" in
        "major")
            major=$((major + 1))
            minor=0
            patch=0
            ;;
        "minor")
            minor=$((minor + 1))
            patch=0
            ;;
        "patch")
            patch=$((patch + 1))
            ;;
        *)
            log_error "Invalid version type: $version_type (use: major, minor, patch)"
            return 1
            ;;
    esac
    
    local new_version="$major.$minor.$patch"
    echo "$new_version" > "$VERSION_FILE"
    log_info "Version updated from $current_version to $new_version"
    echo "$new_version"
}

# Function to check Docker and registry authentication
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        return 1
    fi
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        return 1
    fi
    
    # Check GitHub CLI and authentication
    if command -v gh &> /dev/null; then
        if gh auth status &> /dev/null; then
            log_success "GitHub CLI authenticated"
        else
            log_warning "GitHub CLI not authenticated. Using docker login for GHCR"
        fi
    else
        log_warning "GitHub CLI not found. Ensure you're logged in with: docker login ghcr.io"
    fi
    
    log_success "Prerequisites check completed"
}

# Function to build backend image
build_backend() {
    local version="$1"
    local build_context="$PROJECT_ROOT/backend"
    
    log_info "Building backend image..."
    
    cd "$build_context"
    
    # Build production image
    if docker build \
        --target production \
        --build-arg VERSION="$version" \
        --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
        --build-arg VCS_REF="$(git rev-parse HEAD 2>/dev/null || echo 'unknown')" \
        -t "$BACKEND_IMAGE:$version" \
        -t "$BACKEND_IMAGE:latest" \
        -f Dockerfile \
        .; then
        
        log_success "Backend image built successfully"
        return 0
    else
        log_error "Backend image build failed"
        return 1
    fi
}

# Function to build frontend image
build_frontend() {
    local version="$1"
    local build_context="$PROJECT_ROOT/frontend"
    
    log_info "Building frontend image..."
    
    cd "$build_context"
    
    # Build production image
    if docker build \
        --target production \
        --build-arg VERSION="$version" \
        --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
        --build-arg VCS_REF="$(git rev-parse HEAD 2>/dev/null || echo 'unknown')" \
        -t "$FRONTEND_IMAGE:$version" \
        -t "$FRONTEND_IMAGE:latest" \
        -f Dockerfile \
        .; then
        
        log_success "Frontend image built successfully"
        return 0
    else
        log_error "Frontend image build failed"
        return 1
    fi
}

# Function to test images
test_images() {
    local version="$1"
    
    log_info "Testing built images..."
    
    # Test backend image
    log_info "Testing backend image health check..."
    local backend_container=$(docker run -d \
        -e DATABASE_URL="sqlite:///tmp/test.db" \
        -e REDIS_URL="redis://localhost:6379/0" \
        -e SECRET_KEY="test-secret-key-for-testing-only" \
        -p 0:8000 \
        "$BACKEND_IMAGE:$version")
    
    sleep 10
    
    local backend_port=$(docker port "$backend_container" 8000/tcp | cut -d':' -f2)
    if curl -f "http://localhost:$backend_port/api/v1/health/liveness" &> /dev/null; then
        log_success "Backend image test passed"
        docker stop "$backend_container" &> /dev/null
        docker rm "$backend_container" &> /dev/null
    else
        log_error "Backend image test failed"
        docker logs "$backend_container"
        docker stop "$backend_container" &> /dev/null
        docker rm "$backend_container" &> /dev/null
        return 1
    fi
    
    # Test frontend image
    log_info "Testing frontend image health check..."
    local frontend_container=$(docker run -d \
        -p 0:3000 \
        "$FRONTEND_IMAGE:$version")
    
    sleep 5
    
    local frontend_port=$(docker port "$frontend_container" 3000/tcp | cut -d':' -f2)
    if curl -f "http://localhost:$frontend_port/health" &> /dev/null; then
        log_success "Frontend image test passed"
        docker stop "$frontend_container" &> /dev/null
        docker rm "$frontend_container" &> /dev/null
    else
        log_error "Frontend image test failed"
        docker logs "$frontend_container"
        docker stop "$frontend_container" &> /dev/null
        docker rm "$frontend_container" &> /dev/null
        return 1
    fi
    
    log_success "All image tests passed"
}

# Function to push images to registry
push_images() {
    local version="$1"
    
    log_info "Pushing images to registry..."
    
    # Push backend images
    log_info "Pushing backend image..."
    if docker push "$BACKEND_IMAGE:$version" && docker push "$BACKEND_IMAGE:latest"; then
        log_success "Backend image pushed successfully"
    else
        log_error "Backend image push failed"
        return 1
    fi
    
    # Push frontend images
    log_info "Pushing frontend image..."
    if docker push "$FRONTEND_IMAGE:$version" && docker push "$FRONTEND_IMAGE:latest"; then
        log_success "Frontend image pushed successfully"
    else
        log_error "Frontend image push failed"
        return 1
    fi
    
    log_success "All images pushed successfully"
}

# Function to run security scan on images
security_scan() {
    local version="$1"
    
    log_info "Running security scans on images..."
    
    # Scan backend image
    if command -v trivy &> /dev/null; then
        log_info "Scanning backend image with Trivy..."
        if trivy image --severity HIGH,CRITICAL "$BACKEND_IMAGE:$version"; then
            log_success "Backend image security scan passed"
        else
            log_warning "Backend image has security vulnerabilities"
        fi
        
        log_info "Scanning frontend image with Trivy..."
        if trivy image --severity HIGH,CRITICAL "$FRONTEND_IMAGE:$version"; then
            log_success "Frontend image security scan passed"
        else
            log_warning "Frontend image has security vulnerabilities"
        fi
    else
        log_warning "Trivy not found, skipping security scan"
    fi
}

# Function to generate image manifest
generate_manifest() {
    local version="$1"
    local manifest_file="$PROJECT_ROOT/image-manifest.json"
    
    log_info "Generating image manifest..."
    
    # Get image information
    local backend_digest=$(docker images --digests "$BACKEND_IMAGE:$version" --format "{{.Digest}}")
    local frontend_digest=$(docker images --digests "$FRONTEND_IMAGE:$version" --format "{{.Digest}}")
    
    cat > "$manifest_file" << EOF
{
  "version": "$version",
  "build_date": "$(date -u +'%Y-%m-%dT%H:%M:%SZ')",
  "vcs_ref": "$(git rev-parse HEAD 2>/dev/null || echo 'unknown')",
  "images": {
    "backend": {
      "name": "$BACKEND_IMAGE:$version",
      "digest": "$backend_digest",
      "size": "$(docker images "$BACKEND_IMAGE:$version" --format "{{.Size}}")"
    },
    "frontend": {
      "name": "$FRONTEND_IMAGE:$version", 
      "digest": "$frontend_digest",
      "size": "$(docker images "$FRONTEND_IMAGE:$version" --format "{{.Size}}")"
    }
  },
  "registry": "$REGISTRY",
  "namespace": "$NAMESPACE"
}
EOF

    log_success "Image manifest generated: $manifest_file"
}

# Function to show image status
show_status() {
    local version=$(get_version)
    
    echo "=== SyferStack V2 Container Registry Status ==="
    echo
    echo "📦 Current Version: $version"
    echo "🏷️  Registry: $REGISTRY"
    echo "👤 Namespace: $NAMESPACE"
    echo
    
    echo "🖼️  Local Images:"
    docker images --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}" \
        | grep -E "(syferstackv2|syferstack)" || echo "  No SyferStack images found"
    
    echo
    
    if [ -f "$PROJECT_ROOT/image-manifest.json" ]; then
        echo "📋 Latest Manifest:"
        cat "$PROJECT_ROOT/image-manifest.json" | jq . 2>/dev/null || cat "$PROJECT_ROOT/image-manifest.json"
    else
        echo "📋 No image manifest found"
    fi
}

# Function to clean up old images
cleanup() {
    local keep_versions="${1:-5}"
    
    log_info "Cleaning up old images (keeping latest $keep_versions versions)..."
    
    # Clean backend images
    docker images "$BACKEND_IMAGE" --format "{{.Tag}}" | grep -E '^[0-9]+\.[0-9]+\.[0-9]+$' | \
        sort -V -r | tail -n +$((keep_versions + 1)) | \
        xargs -I {} docker rmi "$BACKEND_IMAGE:{}" 2>/dev/null || true
    
    # Clean frontend images  
    docker images "$FRONTEND_IMAGE" --format "{{.Tag}}" | grep -E '^[0-9]+\.[0-9]+\.[0-9]+$' | \
        sort -V -r | tail -n +$((keep_versions + 1)) | \
        xargs -I {} docker rmi "$FRONTEND_IMAGE:{}" 2>/dev/null || true
    
    # Clean dangling images
    docker image prune -f &> /dev/null || true
    
    log_success "Cleanup completed"
}

# Function to run full build and deploy pipeline
run_pipeline() {
    local version_bump="${1:-patch}"
    local skip_tests="${2:-false}"
    
    log_info "Starting SyferStack V2 build and deploy pipeline..."
    
    # Check prerequisites
    check_prerequisites || return 1
    
    # Update version
    local version=$(update_version "$version_bump")
    
    # Build images
    build_backend "$version" || return 1
    build_frontend "$version" || return 1
    
    # Test images (unless skipped)
    if [ "$skip_tests" != "true" ]; then
        test_images "$version" || return 1
    fi
    
    # Security scan
    security_scan "$version"
    
    # Push images
    push_images "$version" || return 1
    
    # Generate manifest
    generate_manifest "$version"
    
    log_success "Pipeline completed successfully for version $version"
    
    echo
    echo "🚀 Deployment Commands:"
    echo "  docker-compose: SYFERSTACK_VERSION=$version docker-compose -f docker-compose.prod.yml up -d"
    echo "  Kubernetes: kubectl set image deployment/backend backend=$BACKEND_IMAGE:$version"
    echo "  Cloud Run: gcloud run deploy backend --image $BACKEND_IMAGE:$version"
}

# Main script logic
case "${1:-help}" in
    "build")
        version=$(get_version)
        check_prerequisites || exit 1
        build_backend "$version" || exit 1
        build_frontend "$version" || exit 1
        ;;
    "test")
        version=$(get_version)
        test_images "$version"
        ;;
    "push")
        version=$(get_version)
        push_images "$version"
        ;;
    "scan")
        version=$(get_version)
        security_scan "$version"
        ;;
    "pipeline")
        run_pipeline "${2:-patch}" "${3:-false}"
        ;;
    "version")
        case "${2:-get}" in
            "get")
                get_version
                ;;
            "update")
                update_version "${3:-patch}"
                ;;
            *)
                echo "Usage: $0 version {get|update} [major|minor|patch]"
                ;;
        esac
        ;;
    "status")
        show_status
        ;;
    "cleanup")
        cleanup "${2:-5}"
        ;;
    "help"|*)
        echo "SyferStack V2 Container Registry and Deployment System"
        echo ""
        echo "Usage: $0 {build|test|push|scan|pipeline|version|status|cleanup|help}"
        echo ""
        echo "Commands:"
        echo "  build                    - Build Docker images"
        echo "  test                     - Test built images"
        echo "  push                     - Push images to registry"
        echo "  scan                     - Run security scans"
        echo "  pipeline [bump] [skip]   - Run full build pipeline (bump: major|minor|patch, skip: true)"
        echo "  version get              - Show current version"
        echo "  version update [type]    - Update version (major|minor|patch)"
        echo "  status                   - Show registry status"
        echo "  cleanup [keep]           - Clean up old images (default: keep 5)"
        echo "  help                     - Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0 pipeline minor        # Build and deploy with minor version bump"
        echo "  $0 build && $0 test      # Build and test images"
        echo "  $0 push                  # Push current images to registry"
        ;;
esac