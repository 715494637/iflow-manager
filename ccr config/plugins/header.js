const crypto = require('crypto');

class HeaderTransformer {
    name = "header";
    keyIndex = 0;  
    apiKeys = [];  
   
    async transformRequestIn(request, provider) {

        if (this.apiKeys.length === 0 && provider.apiKey) {
            this.apiKeys = provider.apiKey.split(',').map(k => k.trim()).filter(k => k);
        }
        
        const currentApiKey = this.apiKeys[this.keyIndex];
        this.keyIndex = (this.keyIndex + 1) % this.apiKeys.length;
        
        const userAgent = "iFlow-Cli";
        const sessionId = this.generateSessionId();
        const timestamp = Date.now(); 
        const signature = this.generateSignature(userAgent, sessionId, timestamp, currentApiKey);
        
        this.logger?.debug(`当前请求使用密钥索引: ${this.keyIndex}, 密钥: ${currentApiKey?.substring(0, 8)}...`);

        return {
            body: request,
            config: {
                headers: {
                    "user-agent": userAgent,
                    "session-id": sessionId,
                    "conversation-id": "",
                    "x-iflow-timestamp": timestamp.toString(),
                    "x-iflow-signature": signature
                },
            },
        };
    }

    generateSignature(userAgent, sessionId, timestamp, apiKey) {
        if (!apiKey) return null;
        const message = `${userAgent}:${sessionId}:${timestamp}`;
        return crypto
            .createHmac('sha256', apiKey)
            .update(message, 'utf8')
            .digest('hex');
    }

    generateSessionId() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }
}

module.exports = HeaderTransformer;