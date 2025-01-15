from datetime import datetime

def calculate_rating(supabase, occupation, bodypart, age_injury, wpi, adjusted_value):
    """
    Calculate workers compensation rating using Supabase tables.
    
    Args:
        supabase: Initialized Supabase client
        occupation: Occupation title
        bodypart: Body part affected
        age_injury: Date of injury
        wpi: Whole person impairment value
        adjusted_value: Pre-adjusted WPI value
    """
    try:
        # 1. Get group number from occupation
        occupation_response = supabase.table('workers_comp.occupational') \
            .select('occ_group_number') \
            .eq('occ_occupation', occupation) \
            .execute()
            
        if not occupation_response.data:
            raise ValueError(f"No group number found for occupation: {occupation}")
        
        group_number = occupation_response.data[0]['occ_group_number']

        # 2. Get impairment code and variant using group number and bodypart
        variants_response = supabase.table('workers_comp.variants') \
            .select('vari_impairment_code, vari_variant') \
            .eq('vari_groupnumber', group_number) \
            .eq('vari_bodypart', bodypart) \
            .execute()
            
        if not variants_response.data:
            raise ValueError(f"No variants found for group {group_number} and bodypart {bodypart}")
            
        impairment_code = variants_response.data[0]['vari_impairment_code']
        variant = variants_response.data[0]['vari_variant']

        # 3. Get adjustment value from occupational_adjustment
        adjustment_response = supabase.table('workers_comp.occupational_adjustment') \
            .select('adjustment_value') \
            .eq('adjocc_rating', adjusted_value) \
            .execute()
            
        if not adjustment_response.data:
            raise ValueError(f"No adjustment value found for rating: {adjusted_value}")
            
        adjustment_value = adjustment_response.data[0]['adjustment_value']

        # 4. Determine WPI range category
        if wpi < 22:
            wpi_range = "21_and_under"
        elif 22 <= wpi <= 26:
            wpi_range = "22_to_26"
        elif 27 <= wpi <= 31:
            wpi_range = "27_to_31"
        elif 32 <= wpi <= 36:
            wpi_range = "32_to_36"
        elif 37 <= wpi <= 41:
            wpi_range = "37_to_41"
        elif 42 <= wpi <= 46:
            wpi_range = "42_to_46"
        elif 47 <= wpi <= 51:
            wpi_range = "47_to_51"
        elif 52 <= wpi <= 56:
            wpi_range = "52_to_56"
        elif 57 <= wpi <= 61:
            wpi_range = "57_to_61"
        else:
            wpi_range = "62_and_over"

        # 5. Get final value from age_adjustment
        age_response = supabase.table('workers_comp.age_adjustment') \
            .select(wpi_range) \
            .eq('wpi_percent', adjustment_value) \
            .execute()
            
        if not age_response.data:
            raise ValueError(f"No age adjustment found for WPI percent: {adjustment_value}")
            
        final_value = age_response.data[0][wpi_range]

        # 6. Insert results into calculated_med_results
        result_response = supabase.table('workers_comp.calculated_med_results') \
            .insert({
                'occupation': occupation,
                'bodypart': bodypart,
                'age_injury': age_injury,
                'wpi': wpi,
                'occadjusted_value': adjusted_value,
                'fina_result_value': final_value
            }) \
            .execute()

        return {
            'status': 'success',
            'final_value': final_value,
            'details': {
                'group_number': group_number,
                'impairment_code': impairment_code,
                'variant': variant,
                'adjustment_value': adjustment_value,
                'wpi_range': wpi_range
            }
        }

    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }
