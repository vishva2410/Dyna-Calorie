# DynaCalorie Local Demo Debug Log

## Why the 3D Demo / Agent Recording failed:
When attempting to start the local `backend/main.py` FastAPI server to serve the 3D Avatar `index.html` to our automated browser recorder, the core backend crashed instantly during boot.

### The Root Cause:
The backend uses `pydantic-settings` to rigorously validate environment variables before launching. Your `backend/config.py` mandates the presence of:
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `SUPABASE_SERVICE_KEY`

Because the agent is running in an isolated environment without access to your private `.env` file containing your valid Supabase project keys, the backend correctly refused to start and threw a `ValidationError: 3 validation errors for Settings`.

Since the server crashed, the browser agent received an `ERR_CONNECTION_REFUSED` when trying to access `http://localhost:8000/static/index.html` to record the weight loss sliders mapping.

## How you can run it yourself:
To view the 3D Demo yourself locally on your machine:
1. Ensure your authentic `.env` file is located inside the `backend/` directory with your Supabase keys.
2. Run `python3 -m uvicorn backend.main:app --port 8000 --reload` from the project root.
3. Open your browser to `http://127.0.0.1:8000/static/index.html`.
4. Open the Chrome DevTools Console and execute the JS command:
   ```javascript
   window.demoMetrics = JSON.stringify({height_cm: 170, weight_kg: 100, waist_cm: 110, neck_cm: 42, expected_weight_change_kg: -1.0}); window.updateAvatar(window.demoMetrics, 0);
   ```
   Then try advancing the slider integer `window.updateAvatar(window.demoMetrics, 4);` to see the 3D rig morph to simulate 4-weeks of progression!
