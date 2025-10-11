#!/usr/bin/env node

/**
 * Bundle analyzer script for performance monitoring
 * Analyzes build output and provides optimization recommendations
 */

import { execSync } from 'child_process';
import { readFileSync, existsSync } from 'fs';
import { resolve } from 'path';

interface ChunkInfo {
  name: string;
  size: number;
  gzipSize?: number;
  type: 'js' | 'css' | 'asset';
}

interface BundleStats {
  totalSize: number;
  totalGzipSize: number;
  chunks: ChunkInfo[];
  recommendations: string[];
}

class BundleAnalyzer {
  private distPath: string;
  private stats: BundleStats;

  constructor() {
    this.distPath = resolve(process.cwd(), 'dist');
    this.stats = {
      totalSize: 0,
      totalGzipSize: 0,
      chunks: [],
      recommendations: []
    };
  }

  async analyze(): Promise<BundleStats> {
    console.log('🔍 Analyzing bundle...');
    
    if (!existsSync(this.distPath)) {
      throw new Error('Build output not found. Run "npm run build" first.');
    }

    await this.analyzeBuildOutput();
    this.generateRecommendations();
    this.printReport();

    return this.stats;
  }

  private async analyzeBuildOutput(): Promise<void> {
    try {
      // Get file sizes using du command
      const sizeOutput = execSync(`find ${this.distPath} -type f \\( -name "*.js" -o -name "*.css" -o -name "*.html" \\) -exec du -b {} +`, {
        encoding: 'utf8'
      });

      const lines = sizeOutput.trim().split('\n');
      
      for (const line of lines) {
        const [sizeStr, filePath] = line.split('\t');
        const size = parseInt(sizeStr, 10);
        const fileName = filePath.split('/').pop() || '';
        
        let type: 'js' | 'css' | 'asset' = 'asset';
        if (fileName.endsWith('.js')) type = 'js';
        else if (fileName.endsWith('.css')) type = 'css';

        // Try to get gzipped size
        let gzipSize: number | undefined;
        try {
          const gzipOutput = execSync(`gzip -c "${filePath}" | wc -c`, { encoding: 'utf8' });
          gzipSize = parseInt(gzipOutput.trim(), 10);
        } catch (e) {
          // Gzip size not available
        }

        this.stats.chunks.push({
          name: fileName,
          size,
          gzipSize,
          type
        });

        this.stats.totalSize += size;
        if (gzipSize) {
          this.stats.totalGzipSize += gzipSize;
        }
      }

      // Sort chunks by size (largest first)
      this.stats.chunks.sort((a, b) => b.size - a.size);

    } catch (error) {
      console.warn('Could not analyze bundle sizes with system commands, using basic analysis');
      await this.basicAnalysis();
    }
  }

  private async basicAnalysis(): Promise<void> {
    const glob = await import('glob');
    const { statSync } = await import('fs');

    const jsFiles = glob.globSync(resolve(this.distPath, '**/*.js'));
    const cssFiles = glob.globSync(resolve(this.distPath, '**/*.css'));
    
    [...jsFiles, ...cssFiles].forEach(filePath => {
      const stats = statSync(filePath);
      const fileName = filePath.split('/').pop() || '';
      const type = fileName.endsWith('.js') ? 'js' : 'css';

      this.stats.chunks.push({
        name: fileName,
        size: stats.size,
        type: type as 'js' | 'css'
      });

      this.stats.totalSize += stats.size;
    });

    this.stats.chunks.sort((a, b) => b.size - a.size);
  }

  private generateRecommendations(): void {
    const jsChunks = this.stats.chunks.filter(chunk => chunk.type === 'js');
    const cssChunks = this.stats.chunks.filter(chunk => chunk.type === 'css');

    // Check for large chunks
    const largeJsChunks = jsChunks.filter(chunk => chunk.size > 500 * 1024); // > 500KB
    if (largeJsChunks.length > 0) {
      this.stats.recommendations.push(
        `📦 Large JS chunks detected (${largeJsChunks.length} files > 500KB). Consider code splitting.`
      );
    }

    // Check for vendor bundle size
    const vendorChunk = jsChunks.find(chunk => chunk.name.includes('vendor'));
    if (vendorChunk && vendorChunk.size > 1024 * 1024) { // > 1MB
      this.stats.recommendations.push(
        `📚 Vendor bundle is large (${this.formatSize(vendorChunk.size)}). Consider splitting vendor dependencies.`
      );
    }

    // Check total bundle size
    if (this.stats.totalSize > 2 * 1024 * 1024) { // > 2MB
      this.stats.recommendations.push(
        `⚠️  Total bundle size is large (${this.formatSize(this.stats.totalSize)}). Consider lazy loading and tree shaking.`
      );
    }

    // Check for unused CSS
    if (cssChunks.length > 1) {
      this.stats.recommendations.push(
        `🎨 Multiple CSS files detected. Consider CSS bundling and purging unused styles.`
      );
    }

    // Performance recommendations
    if (this.stats.chunks.length > 10) {
      this.stats.recommendations.push(
        `🚀 Many chunks detected (${this.stats.chunks.length}). Consider HTTP/2 server push or bundling strategy.`
      );
    }

    if (this.stats.recommendations.length === 0) {
      this.stats.recommendations.push('✅ Bundle looks optimized! Good job!');
    }
  }

  private printReport(): void {
    console.log('\n📊 Bundle Analysis Report');
    console.log('========================\n');

    console.log(`📈 Total Size: ${this.formatSize(this.stats.totalSize)}`);
    if (this.stats.totalGzipSize > 0) {
      console.log(`🗜️  Gzipped: ${this.formatSize(this.stats.totalGzipSize)} (${Math.round((this.stats.totalGzipSize / this.stats.totalSize) * 100)}% compression)`);
    }
    console.log(`📦 Total Chunks: ${this.stats.chunks.length}\n`);

    console.log('📋 Largest Files:');
    console.log('-----------------');
    this.stats.chunks.slice(0, 10).forEach((chunk, index) => {
      const gzipInfo = chunk.gzipSize ? ` (${this.formatSize(chunk.gzipSize)} gzipped)` : '';
      console.log(`${index + 1}. ${chunk.name} - ${this.formatSize(chunk.size)}${gzipInfo}`);
    });

    if (this.stats.chunks.length > 10) {
      console.log(`... and ${this.stats.chunks.length - 10} more files`);
    }

    console.log('\n💡 Recommendations:');
    console.log('------------------');
    this.stats.recommendations.forEach(rec => console.log(rec));

    console.log('\n🎯 Performance Tips:');
    console.log('-------------------');
    console.log('• Enable gzip/brotli compression on your server');
    console.log('• Use HTTP/2 for better multiplexing');
    console.log('• Consider lazy loading for routes and components');
    console.log('• Implement resource hints (preload, prefetch)');
    console.log('• Monitor bundle size in CI/CD pipeline');
    console.log('• Use tree shaking to eliminate dead code\n');
  }

  private formatSize(bytes: number): string {
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;

    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }

    return `${size.toFixed(1)} ${units[unitIndex]}`;
  }
}

// CLI execution
if (import.meta.url === `file://${process.argv[1]}`) {
  const analyzer = new BundleAnalyzer();
  
  analyzer.analyze()
    .then(() => {
      console.log('✅ Analysis complete!');
      process.exit(0);
    })
    .catch(error => {
      console.error('❌ Analysis failed:', error.message);
      process.exit(1);
    });
}