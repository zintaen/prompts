/**
 * Build script to bundle Vercel Analytics for static site deployment
 */
import { build } from 'esbuild';

async function buildAnalytics() {
  try {
    await build({
      entryPoints: ['assets/analytics.js'],
      bundle: true,
      minify: true,
      format: 'esm',
      outfile: 'assets/analytics.bundle.js',
      platform: 'browser',
    });
    console.log('✓ Analytics bundled successfully');
  } catch (error) {
    console.error('Build failed:', error);
    process.exit(1);
  }
}

buildAnalytics();
