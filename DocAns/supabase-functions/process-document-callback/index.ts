
import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const payload = await req.json()
    console.log('Document processing callback received:', payload);

    const { source_id, content, summary, display_name, title, status, error } = payload

    if (!source_id) {
      return new Response(
        JSON.stringify({ error: 'source_id is required' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Initialize Supabase client
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    // Prepare update data
    const updateData: any = {
      processing_status: status || 'completed',
      updated_at: new Date().toISOString()
    }

    if (content) {
      updateData.content = content
    }

    if (summary) {
      updateData.summary = summary
    }

    // Use title if provided, otherwise use display_name, for backward compatibility
    if (title) {
      updateData.title = title
    } else if (display_name) {
      updateData.title = display_name
    }

    if (error) {
      updateData.processing_status = 'failed'
      console.error('Document processing failed:', error)
    }

    console.log('Updating source with data:', updateData);

    // Update the source record
    const { data, error: updateError } = await supabaseClient
      .from('sources')
      .update(updateData)
      .eq('id', source_id)
      .select()
      .single()

    if (updateError) {
      console.error('Error updating source:', updateError)
      return new Response(
        JSON.stringify({ error: 'Failed to update source', details: updateError }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    console.log('Source updated successfully:', data);

    return new Response(
      JSON.stringify({ success: true, message: 'Source updated successfully', data }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )

  } catch (error) {
    console.error('Error in process-document-callback function:', error)
    return new Response(
      JSON.stringify({ error: 'Internal server error' }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
})
