import React, { useRef, useEffect, useState } from 'react';

// Define Point type
interface Point {
    x: number;
    y: number;
    id?: number; // index
}

interface GaussianParam {
    peak_t: number; // 0-1
    amplitude: number; // 0-1
    sigma: number;
}

interface CurveEditorProps {
    type: 'bezier' | 'gaussian';
    onChange?: (data: any) => void;
}

const CurveEditor: React.FC<CurveEditorProps> = ({ type, onChange }) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const [points, setPoints] = useState<Point[]>([
        { x: 0.1, y: 0.9 }, // normalized 0-1
        { x: 0.3, y: 0.1 },
        { x: 0.7, y: 0.9 },
        { x: 0.9, y: 0.5 }
    ]);

    // For Gaussian: Points represent peaks
    const [gaussians, setGaussians] = useState<GaussianParam[]>([
        { peak_t: 0.3, amplitude: 0.6, sigma: 40 },
        { peak_t: 0.7, amplitude: 0.8, sigma: 30 }
    ]);

    const [draggingIdx, setDraggingIdx] = useState<number | null>(null);

    // Convert normalized coords to canvas coords
    const toCanvas = (p: Point, w: number, h: number) => ({
        x: p.x * w,
        y: p.y * h
    });

    const fromCanvas = (x: number, y: number, w: number, h: number) => ({
        x: Math.min(1, Math.max(0, x / w)),
        y: Math.min(1, Math.max(0, y / h))
    });

    const draw = () => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        // Resize
        const parent = canvas.parentElement;
        if (parent) {
            canvas.width = parent.clientWidth;
            canvas.height = parent.clientHeight;
        }
        const w = canvas.width;
        const h = canvas.height;

        ctx.clearRect(0, 0, w, h);

        // Grid
        ctx.strokeStyle = '#e2e8f0';
        ctx.lineWidth = 1;
        ctx.setLineDash([5, 5]);
        ctx.beginPath();
        ctx.moveTo(0, h/2);
        ctx.lineTo(w, h/2);
        ctx.stroke();
        ctx.setLineDash([]);

        ctx.lineWidth = 3;
        ctx.strokeStyle = '#4d7cfe';

        if (type === 'bezier') {
            // Draw Bezier
            // We use the points as control points for a cubic bezier (approx)
            // Or just a spline. Let's do a simple Catmull-Rom or just lines for simplicity in this prototype,
            // OR standard cubic bezier if we have exactly 4 points.
            // Let's assume points are [Start, CP1, CP2, End]
            const p = points.map(pt => toCanvas(pt, w, h));

            ctx.beginPath();
            ctx.moveTo(p[0].x, p[0].y);
            ctx.bezierCurveTo(p[1].x, p[1].y, p[2].x, p[2].y, p[3].x, p[3].y);
            ctx.stroke();

            // Draw Handles
            ctx.strokeStyle = '#a0aec0';
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(p[0].x, p[0].y);
            ctx.lineTo(p[1].x, p[1].y);
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(p[3].x, p[3].y);
            ctx.lineTo(p[2].x, p[2].y);
            ctx.stroke();

            // Draw Points
            ctx.fillStyle = '#4d7cfe';
            p.forEach((pt, i) => {
                ctx.beginPath();
                ctx.arc(pt.x, pt.y, 6, 0, Math.PI * 2);
                ctx.fill();
            });

        } else {
            // Draw Gaussian Sum
            ctx.beginPath();
            ctx.moveTo(0, h); // Start bottom left

            for (let x = 0; x <= w; x += 2) {
                const t = x / w;
                let yVal = 0;
                gaussians.forEach(g => {
                    // Gaussian function: A * exp(-(x-b)^2 / (2c^2))
                    // x is pixel, b is peak_t * w, c is sigma
                    const center = g.peak_t * w;
                    const val = g.amplitude * 100 * Math.exp(-Math.pow((x - center), 2) / (2 * g.sigma * g.sigma));
                    yVal += val;
                });
                ctx.lineTo(x, h - yVal - 10); // 10px padding from bottom
            }
            ctx.stroke();

            // Draw Handles (Peaks)
            ctx.fillStyle = '#f6ad55';
            gaussians.forEach(g => {
                const cx = g.peak_t * w;
                // Height based on amplitude roughly
                const cy = h - (g.amplitude * 100) - 10;
                ctx.beginPath();
                ctx.arc(cx, cy, 6, 0, Math.PI * 2);
                ctx.fill();
            });
        }
    };

    useEffect(() => {
        draw();
        // Notify parent of change
        if (onChange) {
            if (type === 'bezier') onChange(points);
            else onChange(gaussians);
        }
    }, [points, gaussians]);

    const handleMouseDown = (e: React.MouseEvent) => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        // Hit detection
        if (type === 'bezier') {
            const w = canvas.width;
            const h = canvas.height;
            points.forEach((p, i) => {
                const cx = p.x * w;
                const cy = p.y * h;
                if (Math.hypot(x - cx, y - cy) < 10) {
                    setDraggingIdx(i);
                }
            });
        } else {
            const w = canvas.width;
            const h = canvas.height;
            gaussians.forEach((g, i) => {
                const cx = g.peak_t * w;
                const cy = h - (g.amplitude * 100) - 10;
                if (Math.hypot(x - cx, y - cy) < 10) {
                    setDraggingIdx(i);
                }
            });
        }
    };

    const handleMouseMove = (e: React.MouseEvent) => {
        if (draggingIdx === null) return;
        const canvas = canvasRef.current;
        if (!canvas) return;
        const rect = canvas.getBoundingClientRect();

        const w = canvas.width;
        const h = canvas.height;

        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        if (type === 'bezier') {
            const newPoints = [...points];
            const normalized = fromCanvas(x, y, w, h);
            newPoints[draggingIdx] = normalized;
            setPoints(newPoints);
        } else {
            const newGaussians = [...gaussians];
            const normalizedX = Math.min(1, Math.max(0, x / w));
            // Invert Y for amplitude (top is 1)
            // Approx amplitude from Y
            const amp = Math.min(1, Math.max(0, (h - y - 10) / 100));

            newGaussians[draggingIdx] = {
                ...newGaussians[draggingIdx],
                peak_t: normalizedX,
                amplitude: amp
            };
            setGaussians(newGaussians);
        }
    };

    const handleMouseUp = () => {
        setDraggingIdx(null);
    };

    return (
        <canvas
            ref={canvasRef}
            className="w-full h-full cursor-pointer touch-none"
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
        />
    );
};

export default CurveEditor;
