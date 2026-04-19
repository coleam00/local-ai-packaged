
import "https://deno.land/x/xhr@0.1.0/mod.ts";
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const openAIApiKey = Deno.env.get('OPENAI_API_KEY');

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

serve(async (req) => {
  // Handle CORS preflight requests
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const { content } = await req.json();

    if (!content) {
      return new Response(
        JSON.stringify({ error: 'Content is required' }), 
        { 
          status: 400, 
          headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
        }
      );
    }

    // Parse content if it's a structured AI response
    let textContent = content;
    try {
      const parsed = JSON.parse(content);
      if (parsed.segments && parsed.segments.length > 0) {
        // Extract text from first few segments
        textContent = parsed.segments
          .slice(0, 3)
          .map((segment: any) => segment.text)
          .join(' ');
      }
    } catch (e) {
      // Content is already plain text
    }

    // Truncate content to avoid token limits
    const truncatedContent = textContent.substring(0, 1000);

    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${openAIApiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: 'gpt-4o-mini',
        messages: [
          { 
            role: 'system', 
            content: 'You are a helpful assistant that generates concise, descriptive titles. Generate a title that is exactly 5 words or fewer, capturing the main topic or theme of the content. Return only the title, nothing else.' 
          },
          { 
            role: 'user', 
            content: `Generate a 5-word title for this content: ${truncatedContent}` 
          }
        ],
        max_tokens: 20,
        temperature: 0.7,
      }),
    });

    if (!response.ok) {
      throw new Error(`OpenAI API error: ${response.status}`);
    }

    const data = await response.json();
    const generatedTitle = data.choices[0].message.content.trim();

    console.log('Generated title:', generatedTitle);

    return new Response(
      JSON.stringify({ title: generatedTitle }), 
      {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      }
    );
  } catch (error) {
    console.error('Error in generate-note-title function:', error);
    return new Response(
      JSON.stringify({ error: error.message }), 
      {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      }
    );
  }
});
