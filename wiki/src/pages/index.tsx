import type {ReactNode} from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';

import styles from './index.module.css';

function HomepageHeader() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <header className={clsx('hero hero--primary', styles.heroBanner)}>
      <div className="container">
        <Heading as="h1" className="hero__title">
          {siteConfig.title}
        </Heading>
        <p className="hero__subtitle">{siteConfig.tagline}</p>
        <div className={styles.buttons}>
          <Link
            className="button button--secondary button--lg"
            to="/docs">
            Start Reading
          </Link>
        </div>
      </div>
    </header>
  );
}

export default function Home(): ReactNode {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout
      title={`Hello from ${siteConfig.title}`}
      description="Description will go into a meta tag in <head />">
      <HomepageHeader />
      <main>
        <section style={{padding: '2rem 0', textAlign: 'center', maxWidth: '900px', margin: '0 auto', paddingLeft: '1rem', paddingRight: '1rem'}}>
          <Heading as="h2">What You'll Find Here</Heading>
          <p style={{fontSize: '1.1rem', lineHeight: '1.6', marginTop: '1rem'}}>
            This wiki documents the <strong>QKDN Agent Simulator</strong> — a backend system that simulates a Quantum Key Distribution Network with a single KMS node, an SDN Agent, and multiple clients.
          </p>
          <p style={{fontSize: '1.1rem', lineHeight: '1.6'}}>
            The documentation is divided into two parts:
          </p>
          <div style={{textAlign: 'left', maxWidth: '600px', margin: '1.5rem auto'}}>
            <div style={{marginBottom: '1.5rem'}}>
              <Heading as="h3" style={{fontSize: '1.3rem', marginBottom: '0.5rem'}}>Background</Heading>
              <p>Foundational concepts from classical cryptography through quantum threats to QKD infrastructure.</p>
            </div>
            <div>
              <Heading as="h3" style={{fontSize: '1.3rem', marginBottom: '0.5rem'}}>System Architecture</Heading>
              <p>Deep dive into the simulator's components, provisioning flows, resilience mechanisms, and how to run it.</p>
            </div>
          </div>
        </section>
      </main>
    </Layout>
  );
}
