import './globals.css';
import type { Metadata } from 'next';
import { Playfair_Display, Space_Grotesk, Space_Mono } from 'next/font/google';
import Layout from '../components/Layout';

const playfair = Playfair_Display({ subsets: ['latin'], variable: '--font-playfair', weight: ['400', '700'] });
const spaceGrotesk = Space_Grotesk({ subsets: ['latin'], variable: '--font-space-grotesk', weight: ['300', '400', '600', '700'] });
const spaceMono = Space_Mono({ subsets: ['latin'], variable: '--font-space-mono', weight: ['400', '700'] });

export const metadata: Metadata = {
    title: 'The Chronos Daily | Vertex AI Media Search',
    description: 'Vertex AI Search media demo with Chronos Daily theme',
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="en">
            <body className={`${spaceGrotesk.variable} ${spaceMono.variable} ${playfair.variable}`}>
                <Layout>{children}</Layout>
            </body>
        </html>
    );
}
