require('dotenv').config({ path: '../../.env' });
const express = require('express');
const cors = require('cors');
const morgan = require('morgan');
const axios = require('axios');
const Ajv = require('ajv');
const addFormats = require('ajv-formats');
const fs = require('fs');
const path = require('path');

// Prefilters and Postfilters
const prefilters = require('../prefilters');
const postfilters = require('../postfilters');

const app = express();
const ajv = new Ajv();
addFormats(ajv);

app.use(cors());
app.use(express.json());
app.use(morgan('combined'));

// Load Schema
const requestSchema = JSON.parse(fs.readFileSync(path.join(__dirname, '../../spec/schema/request.json'), 'utf8'));
const validateRequest = ajv.compile(requestSchema);

const PORT = process.env.PORT || 3000;
const FAIL_CLOSED = process.env.FAIL_CLOSED === 'true';

app.post('/api/reflect', async (req, res) => {
    const startTime = Date.now();
    let { session_id, request_id, input, profile = 'DEFAULT' } = req.body;

    // 1. Validate Schema
    if (!validateRequest(req.body)) {
        return res.status(400).json({ error: 'Invalid request schema', details: validateRequest.errors });
    }

    try {
        // 2. Prefilters
        const preResult = await prefilters.run(req.body);
        if (preResult.outcome === 'refused') {
            return res.status(403).json(buildResponse(req.body, 'I cannot process this request based on safety policy.', 'refused', startTime));
        }

        // Update input if rewritten by prefilters
        if (preResult.outcome === 'rewritten') {
            input = preResult.input;
        }

        // 3. Inference
        const backendUrl = process.env.LOCAL_BACKEND_URL || 'http://localhost:11434/api/generate';
        const model = process.env.LOCAL_BACKEND_MODEL || 'mirrorbrain-ami:latest';

        // Simple Ollama call for reference
        const response = await axios.post(backendUrl, {
            model: model,
            prompt: input,
            stream: false
        }).catch(err => {
            throw new Error(`Backend unreachable: ${err.message}`);
        });

        let output = response.data.response || response.data.output;

        // 4. Postfilters
        const postResult = await postfilters.run(output, profile);
        if (postResult.outcome === 'refused') {
            return res.status(403).json(buildResponse(req.body, 'The generated response was blocked by safety policy.', 'refused', startTime));
        }

        output = postResult.output;
        const finalOutcome = postResult.outcome === 'rewritten' || preResult.outcome === 'rewritten' ? 'rewritten' : 'allowed';

        // 5. Final Response
        return res.status(200).json(buildResponse(req.body, output, finalOutcome, startTime, model));

    } catch (error) {
        console.error('MirrorGate Error:', error.message);
        if (FAIL_CLOSED) {
            return res.status(500).json(buildResponse(req.body, 'Internal safety proxy error. Fail-closed activated.', 'refused', startTime));
        }
        return res.status(500).json({ error: error.message });
    }
});

function buildResponse(reqBody, output, outcome, startTime, model = 'unknown') {
    return {
        request_id: reqBody.request_id,
        session_id: reqBody.session_id,
        output: output,
        safety_outcome: outcome,
        model_used: model,
        rule_version: 'v1.0.0',
        policy_profile: reqBody.profile || 'DEFAULT',
        stats: {
            processing_time_ms: Date.now() - startTime
        }
    };
}

app.listen(PORT, () => {
    console.log(`⟡ MirrorGate Proxy ONLINE on port ${PORT}`);
});
