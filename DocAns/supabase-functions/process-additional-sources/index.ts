
import { serve } from "https://deno.land/std@0.168.0/http/server.ts"

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

serve(async (req) => {
  // Handle CORS preflight requests
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const { type, notebookId, urls, title, content, timestamp, sourceIds } = await req.json();
    
    console.log(`Process additional sources received ${type} request for notebook ${notebookId}`);

    // Get the webhook URL from Supabase secrets
    const webhookUrl = Deno.env.get('ADDITIONAL_SOURCES_WEBHOOK_URL');
    if (!webhookUrl) {
      throw new Error('ADDITIONAL_SOURCES_WEBHOOK_URL not configured');
    }

    // Get the auth token from Supabase secrets (same as generate-notebook-content)
    const authToken = Deno.env.get('NOTEBOOK_GENERATION_AUTH');
    if (!authToken) {
      throw new Error('NOTEBOOK_GENERATION_AUTH not configured');
    }

    // Prepare the webhook payload
    let webhookPayload;
    
    if (type === 'multiple-websites') {
      webhookPayload = {
        type: 'multiple-websites',
        notebookId,
        urls,
        sourceIds, // Array of source IDs corresponding to the URLs
        timestamp
      };
    } else if (type === 'copied-text') {
      webhookPayload = {
        type: 'copied-text',
        notebookId,
        title,
        content,
        sourceId: sourceIds?.[0], // Single source ID for copied text
        timestamp
      };
    } else {
      throw new Error(`Unsupported type: ${type}`);
    }

    console.log('Sending webhook payload:', JSON.stringify(webhookPayload, null, 2));

    // Send to webhook with authentication
    const response = await fetch(webhookUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': authToken,
        ...corsHeaders
      },
      body: JSON.stringify(webhookPayload)
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Webhook request failed:', response.status, errorText);
      throw new Error(`Webhook request failed: ${response.status} - ${errorText}`);
    }

    const webhookResponse = await response.text();
    console.log('Webhook response:', webhookResponse);

    return new Response(JSON.stringify({ 
      success: true, 
      message: `${type} data sent to webhook successfully`,
      webhookResponse 
    }), {
      headers: { 
        'Content-Type': 'application/json',
        ...corsHeaders 
      },
    });

  } catch (error) {
    console.error('Process additional sources error:', error);
    
    return new Response(JSON.stringify({ 
      error: error.message,
      success: false 
    }), {
      status: 500,
      headers: { 
        'Content-Type': 'application/json',
        ...corsHeaders 
      },
    });
  }
});
